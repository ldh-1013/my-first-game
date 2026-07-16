from __future__ import annotations

import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from itertools import groupby
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    DailyPrice,
    FinancialSnapshot,
    HistoricalReplayRun,
    NewsArticle,
    NewsStockLink,
    PredictionResult,
    SentimentScore,
    Stock,
)
from app.services.analysis_runner import normalize_ticker
from app.services.backtest_service import (
    absolute_forecast_error,
    direction_for_return,
    direction_hit,
    range_hit_for_return,
)
from app.services.prediction_engine import RuleBasedPredictionModel
from app.services.price_collector import fetch_daily_prices
from app.services.quality_service import financial_score, load_scoring_weights
from app.services.recommendation_engine import SAMPLE_UNIVERSE
from app.services.scoring_engine import (
    calculate_final_score,
    calculate_risk_score,
    calculate_technical_score,
    calculate_volume_score,
)
from app.services.sentiment_analyzer import aggregate_sentiment
from app.services.technical_indicator import calculate_indicators
from app.utils.logger import get_logger

logger = get_logger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="historical-replay")
ACTIVE_REPLAY_STATUSES = {"queued", "running"}
DEFAULT_AUTO_VALIDATION_MARKETS = ["KR", "US"]
DEFAULT_AUTO_VALIDATION_SCOPE = "current_analysis_universe"
DEFAULT_AUTO_VALIDATION_LOOKBACK_YEARS = 2
DEFAULT_AUTO_VALIDATION_HORIZON_DAYS = 1


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _today_kst() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def latest_replay_run(db: Session) -> HistoricalReplayRun | None:
    return db.scalar(
        select(HistoricalReplayRun)
        .order_by(HistoricalReplayRun.created_at.desc(), HistoricalReplayRun.id.desc())
        .limit(1)
    )


def latest_active_replay_run(db: Session) -> HistoricalReplayRun | None:
    return db.scalar(
        select(HistoricalReplayRun)
        .where(HistoricalReplayRun.status.in_(ACTIVE_REPLAY_STATUSES))
        .order_by(HistoricalReplayRun.created_at.desc(), HistoricalReplayRun.id.desc())
        .limit(1)
    )


def _run_refresh_date(run: HistoricalReplayRun) -> date | None:
    if run.created_at:
        return run.created_at.replace(tzinfo=UTC).astimezone(
            ZoneInfo("Asia/Seoul")
        ).date()
    return run.end_date


def _append_run_error(run: HistoricalReplayRun, message: str) -> None:
    try:
        errors = json.loads(run.error_log or "[]")
    except json.JSONDecodeError:
        errors = []
    errors.append({"error": message})
    run.error_log = json.dumps(errors[-100:], ensure_ascii=False)


def reconcile_historical_replay_runs(
    db: Session,
    *,
    assume_orphaned: bool = False,
    stale_after_minutes: int = 720,
) -> int:
    """Mark replay runs that cannot make progress anymore as failed.

    Startup recovery uses assume_orphaned=True because the in-memory executor
    that owned queued/running work is gone after an app restart. During normal
    API polling we only repair very old stale rows.
    """
    now = _utcnow()
    cutoff = now - timedelta(minutes=stale_after_minutes)
    repaired = 0
    rows = list(
        db.scalars(
            select(HistoricalReplayRun).where(
                HistoricalReplayRun.status.in_(ACTIVE_REPLAY_STATUSES)
            )
        ).all()
    )
    for run in rows:
        reference_time = run.started_at or run.created_at
        if not assume_orphaned and reference_time and reference_time > cutoff:
            continue
        run.status = "failed"
        run.progress_stage = "failed"
        run.current_ticker = None
        run.current_date = None
        run.completed_at = now
        _append_run_error(
            run,
            "앱 재시작 또는 장시간 무응답으로 예측 검증 작업을 정리했습니다. 다음 자동 갱신에서 다시 실행됩니다.",
        )
        repaired += 1
    if repaired:
        db.commit()
    return repaired


def recover_historical_replay_runs_on_startup() -> int:
    with SessionLocal() as db:
        repaired = reconcile_historical_replay_runs(db, assume_orphaned=True)
        if repaired:
            logger.warning("Recovered %s orphaned historical replay run(s)", repaired)
        return repaired


def ensure_daily_validation_run(
    db: Session,
    *,
    today: date | None = None,
    force: bool = False,
) -> tuple[HistoricalReplayRun, bool, str]:
    """Start one daily prediction-validation refresh when today's run is missing."""
    refresh_day = today or _today_kst()
    reconcile_historical_replay_runs(db)
    active = latest_active_replay_run(db)
    if active and not force:
        return active, False, "already_running"

    latest = latest_replay_run(db)
    if latest and not force and _run_refresh_date(latest) == refresh_day:
        return latest, False, "already_refreshed_today"

    run = create_replay_run(
        db,
        lookback_years=DEFAULT_AUTO_VALIDATION_LOOKBACK_YEARS,
        markets=DEFAULT_AUTO_VALIDATION_MARKETS,
        scope=DEFAULT_AUTO_VALIDATION_SCOPE,
        horizon_days=DEFAULT_AUTO_VALIDATION_HORIZON_DAYS,
        force_rebuild=False,
        as_of_date=refresh_day,
    )
    return run, True, "started"


@dataclass
class HistoricalContext:
    news: list[tuple[date, dict]]
    financials: list[FinancialSnapshot]


class WalkForwardCalibrator:
    """Online calibration state. It only learns after each simulated outcome."""

    def __init__(self) -> None:
        self.bucket_market: dict[tuple[str, int], list[int]] = defaultdict(
            lambda: [0, 0]
        )
        self.bucket_global: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        self.direction_market: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    @staticmethod
    def bucket(probability: float) -> int:
        return max(0, min(90, int(probability // 10) * 10))

    def calibrate(self, probability: float, market: str) -> tuple[float, int, float | None]:
        bucket = self.bucket(probability)
        market_count, market_up = self.bucket_market[(market, bucket)]
        global_count, global_up = self.bucket_global[bucket]
        if market_count >= 50:
            count, up = market_count, market_up
        else:
            count, up = global_count, global_up
        if count == 0:
            return round(probability, 1), 0, None
        prior_strength = 20.0
        raw_rate = probability / 100
        posterior = (up + raw_rate * prior_strength) / (count + prior_strength)
        evidence_weight = count / (count + 100)
        calibrated = raw_rate * (1 - evidence_weight) + posterior * evidence_weight
        return round(max(5, min(95, calibrated * 100)), 1), count, round(up / count * 100, 1)

    def confidence(self, market: str, base_confidence: str) -> str:
        count, correct = self.direction_market[market]
        if count < 30:
            return "very_low"
        if count < 100 or base_confidence == "low":
            return "low"
        accuracy = correct / count * 100
        if accuracy < 42:
            return "very_low"
        if accuracy < 50:
            return "low"
        if accuracy >= 58 and count >= 200:
            return "high"
        return "medium"

    def update(
        self,
        probability: float,
        market: str,
        actual_direction: str,
        is_correct: bool | None,
    ) -> None:
        if actual_direction not in {"up", "down"}:
            return
        bucket = self.bucket(probability)
        market_stats = self.bucket_market[(market, bucket)]
        global_stats = self.bucket_global[bucket]
        market_stats[0] += 1
        global_stats[0] += 1
        if actual_direction == "up":
            market_stats[1] += 1
            global_stats[1] += 1
        if is_correct is not None:
            direction_stats = self.direction_market[market]
            direction_stats[0] += 1
            direction_stats[1] += int(is_correct)


def _safe_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def next_trading_outcome(
    price_history: pd.DataFrame,
    as_of_date: date,
    horizon_days: int = 1,
) -> tuple[date, float]:
    """Return the actual next available trading row, not a calendar-day guess."""
    ordered = price_history.sort_index()
    eligible = [
        index
        for index, timestamp in enumerate(ordered.index)
        if pd.Timestamp(timestamp).date() <= as_of_date
    ]
    if not eligible:
        raise ValueError("예측일 가격을 찾을 수 없습니다.")
    base_index = eligible[-1]
    target_index = base_index + max(1, horizon_days)
    if target_index >= len(ordered):
        raise ValueError("실제 다음 거래일 가격이 아직 없습니다.")
    base_close = float(ordered.iloc[base_index]["close"])
    target_close = float(ordered.iloc[target_index]["close"])
    actual_return = (target_close / base_close - 1) * 100
    return pd.Timestamp(ordered.index[target_index]).date(), actual_return


def _latest_as_dict(frame: pd.DataFrame) -> dict | None:
    if frame.empty:
        return None
    return {key: _safe_float(value) for key, value in frame.iloc[-1].items()}


def _raw_frame_from_database(db: Session, stock_id: int) -> pd.DataFrame:
    rows = list(
        db.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_id == stock_id,
                DailyPrice.close_price.is_not(None),
            )
            .order_by(DailyPrice.date.asc())
        ).all()
    )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "open": row.open_price,
                "high": row.high_price,
                "low": row.low_price,
                "close": row.close_price,
                "adjusted_close": row.adjusted_close,
                "volume": row.volume,
            }
            for row in rows
        ],
        index=pd.to_datetime([row.date for row in rows]),
    ).dropna(subset=["open", "high", "low", "close", "volume"])


def _persist_price_history(
    db: Session,
    stock: Stock,
    prepared: pd.DataFrame,
) -> None:
    existing = {
        row.date: row
        for row in db.scalars(
            select(DailyPrice).where(DailyPrice.stock_id == stock.id)
        ).all()
    }
    for index, row in prepared.iterrows():
        row_date = pd.Timestamp(index).date()
        values = {
            "open_price": _safe_float(row.get("open")),
            "high_price": _safe_float(row.get("high")),
            "low_price": _safe_float(row.get("low")),
            "close_price": _safe_float(row.get("close")),
            "adjusted_close": _safe_float(row.get("adjusted_close")),
            "volume": _safe_float(row.get("volume")),
            "change_rate": _safe_float(row.get("change_rate")),
            "ma5": _safe_float(row.get("ma5")),
            "ma20": _safe_float(row.get("ma20")),
            "ma60": _safe_float(row.get("ma60")),
            "rsi": _safe_float(row.get("rsi")),
            "atr": _safe_float(row.get("atr")),
            "volatility_20d": _safe_float(row.get("volatility_20d")),
            "volume_change_rate": _safe_float(row.get("volume_change_rate")),
        }
        values["trading_value"] = (
            values["close_price"] * values["volume"]
            if values["close_price"] is not None and values["volume"] is not None
            else None
        )
        target = existing.get(row_date)
        if target is None:
            db.add(DailyPrice(stock_id=stock.id, date=row_date, **values))
        else:
            for key, value in values.items():
                setattr(target, key, value)


def _load_historical_context(db: Session, stock: Stock) -> HistoricalContext:
    news_rows = db.execute(
        select(
            NewsArticle.published_at,
            SentimentScore.sentiment_score,
            SentimentScore.confidence,
        )
        .join(NewsStockLink, NewsStockLink.article_id == NewsArticle.id)
        .join(
            SentimentScore,
            (SentimentScore.article_id == NewsArticle.id)
            & (SentimentScore.stock_id == stock.id),
        )
        .where(
            NewsStockLink.stock_id == stock.id,
            NewsArticle.published_at.is_not(None),
        )
        .order_by(NewsArticle.published_at.asc())
    ).all()
    news = [
        (
            published_at.date(),
            {
                "sentiment_score": float(sentiment_score),
                "confidence": confidence,
            },
        )
        for published_at, sentiment_score, confidence in news_rows
        if published_at is not None
    ]
    financials = list(
        db.scalars(
            select(FinancialSnapshot)
            .where(FinancialSnapshot.stock_id == stock.id)
            .order_by(FinancialSnapshot.as_of_date.asc())
        ).all()
    )
    return HistoricalContext(news=news, financials=financials)


def _point_in_time_inputs(
    context: HistoricalContext,
    as_of_date: date,
) -> tuple[list[dict], FinancialSnapshot | None]:
    news_start = as_of_date - timedelta(days=7)
    news = [
        payload
        for published_at, payload in context.news
        if news_start <= published_at <= as_of_date
    ]
    financial = next(
        (
            snapshot
            for snapshot in reversed(context.financials)
            if snapshot.as_of_date <= as_of_date
        ),
        None,
    )
    return news, financial


def build_prediction_for_date(
    db: Session,
    stock: Stock,
    price_history: pd.DataFrame,
    as_of_date: date,
    *,
    mode: str = "historical_replay",
    indicators_ready: bool = False,
    historical_context: HistoricalContext | None = None,
    weights: dict[str, float] | None = None,
) -> dict:
    """Build a prediction using only rows and auxiliary data known by as_of_date."""
    cutoff = pd.Timestamp(as_of_date)
    sliced = price_history.loc[price_history.index <= cutoff].copy()
    if sliced.empty:
        raise ValueError("예측일 이전 가격 데이터가 없습니다.")
    prepared = sliced if indicators_ready else calculate_indicators(sliced)
    latest = _latest_as_dict(prepared)
    if not latest or latest.get("close") is None:
        raise ValueError("예측일 종가를 확인할 수 없습니다.")

    context = historical_context or HistoricalContext(news=[], financials=[])
    historical_news, historical_financial = _point_in_time_inputs(context, as_of_date)
    news_available = bool(historical_news)
    financial_available = historical_financial is not None
    news_score = aggregate_sentiment(historical_news) if news_available else 0.0
    finance_score = financial_score(historical_financial) if financial_available else 0.0
    technical_score = calculate_technical_score(latest)
    volume_score = calculate_volume_score(latest)
    # Missing historical news is neutral, not a risk penalty. The limitation is
    # carried separately in data_quality_note and confidence.
    risk_score = calculate_risk_score(
        latest,
        has_news=True if mode == "historical_replay" else news_available,
        is_listed=stock.is_listed,
    )
    final_score = calculate_final_score(
        news_score=news_score,
        technical_score=technical_score,
        volume_score=volume_score,
        financial_score=finance_score,
        risk_score=risk_score,
        weights=weights or load_scoring_weights(db),
    )
    prediction = RuleBasedPredictionModel().predict(
        final_score=final_score,
        volatility=latest.get("volatility_20d"),
        data_points=len(prepared),
    )
    quality_notes = ["historical_price_only"]
    if news_available:
        quality_notes.append("historical_news_available")
    if financial_available:
        quality_notes.append("historical_financial_available")
    if len(prepared) < 60:
        quality_notes.append("incomplete")
    return {
        **prediction,
        "raw_up_probability": prediction["up_probability"],
        "final_score": final_score,
        "latest": latest,
        "historical_news_available": news_available,
        "historical_financial_available": financial_available,
        "data_quality_note": ",".join(quality_notes),
        "feature_snapshot": {
            "as_of_date": as_of_date.isoformat(),
            "price_rows": len(prepared),
            "close": latest.get("close"),
            "technical_score": technical_score,
            "volume_score": volume_score,
            "news_score": news_score,
            "financial_score": finance_score,
            "risk_score": risk_score,
            "volatility_20d": latest.get("volatility_20d"),
            "rsi": latest.get("rsi"),
            "recent_5d_return": latest.get("recent_5d_return"),
            "recent_20d_return": latest.get("recent_20d_return"),
            "ma5_gap": (
                (latest["close"] / latest["ma5"] - 1) * 100
                if latest.get("close") and latest.get("ma5")
                else None
            ),
            "ma20_gap": (
                (latest["close"] / latest["ma20"] - 1) * 100
                if latest.get("close") and latest.get("ma20")
                else None
            ),
            "macd": latest.get("macd"),
            "atr": latest.get("atr"),
            "volume_change_rate": latest.get("volume_change_rate"),
            "mode": mode,
        },
    }


def _ensure_sample_stocks(db: Session) -> None:
    for item in SAMPLE_UNIVERSE:
        ticker = normalize_ticker(item["ticker"], item.get("market"))
        if db.scalar(select(Stock.id).where(Stock.ticker == ticker)):
            continue
        market = item.get("market", "US")
        db.add(
            Stock(
                ticker=ticker,
                name=item.get("name") or ticker,
                market=market,
                country="KR" if market == "KR" else "US",
                currency=item.get("currency") or ("KRW" if market == "KR" else "USD"),
                is_listed=True,
                asset_type="LISTED_STOCK",
                data_source="yfinance",
            )
        )
    db.flush()


def replay_candidates(db: Session, markets: Iterable[str]) -> list[Stock]:
    _ensure_sample_stocks(db)
    selected_markets = {market.upper() for market in markets}
    return list(
        db.scalars(
            select(Stock)
            .where(Stock.market.in_(selected_markets))
            .order_by(Stock.market.asc(), Stock.ticker.asc())
        ).all()
    )


def replay_universe(db: Session, markets: Iterable[str]) -> list[Stock]:
    return [
        stock
        for stock in replay_candidates(db, markets)
        if stock.is_listed and stock.asset_type != "PRIVATE"
    ]


def _seed_calibrator(
    db: Session,
    calibrator: WalkForwardCalibrator,
    start_date: date,
) -> None:
    rows = db.execute(
        select(PredictionResult, Stock.market)
        .join(Stock, Stock.id == PredictionResult.stock_id)
        .where(
            PredictionResult.prediction_source == "historical_replay",
            PredictionResult.model_version == RuleBasedPredictionModel.version,
            PredictionResult.prediction_date < start_date,
            PredictionResult.actual_direction.in_(["up", "down"]),
            PredictionResult.raw_up_probability.is_not(None),
        )
        .order_by(PredictionResult.prediction_date.asc())
    ).all()
    for prediction, market in rows:
        calibrator.update(
            prediction.raw_up_probability,
            market,
            prediction.actual_direction,
            prediction.is_correct,
        )


def run_historical_replay(db: Session, run: HistoricalReplayRun) -> None:
    run.status = "running"
    run.progress_stage = "loading_prices"
    run.started_at = _utcnow()
    db.commit()
    errors: list[dict] = []
    stock_frames: dict[int, pd.DataFrame] = {}
    contexts: dict[int, HistoricalContext] = {}
    tasks: list[tuple[date, int, int]] = []

    try:
        markets = [value for value in run.market_scope.split(",") if value]
        stocks = replay_candidates(db, markets)
        db.commit()
        for stock in stocks:
            run.current_ticker = stock.ticker
            run.current_date = None
            db.commit()
            if not stock.is_listed or stock.asset_type == "PRIVATE":
                errors.append(
                    {
                        "ticker": stock.ticker,
                        "error": "가격 기반 과거 검증 불가: 일별 시장 종가 데이터 부족",
                    }
                )
                run.failed_tasks += 1
                continue
            raw = fetch_daily_prices(stock.ticker, period="3y")
            if raw.empty:
                raw = _raw_frame_from_database(db, stock.id)
            if raw.empty or len(raw) < 2:
                errors.append(
                    {
                        "ticker": stock.ticker,
                        "error": "가격 기반 과거 검증 불가: 일별 시장 종가 데이터 부족",
                    }
                )
                run.failed_tasks += 1
                continue
            raw = raw.sort_index()
            raw.index = pd.to_datetime(raw.index).tz_localize(None)
            prepared = calculate_indicators(raw)
            _persist_price_history(db, stock, prepared)
            stock_frames[stock.id] = prepared
            contexts[stock.id] = _load_historical_context(db, stock)
            dates = [pd.Timestamp(index).date() for index in prepared.index]
            for index, prediction_date in enumerate(dates):
                target_index = index + run.horizon_days
                if (
                    prediction_date < run.start_date
                    or prediction_date > run.end_date
                    or target_index >= len(dates)
                ):
                    continue
                tasks.append((prediction_date, stock.id, index))
            db.commit()

        tasks.sort(key=lambda item: (item[0], item[1]))
        run.total_tasks = len(tasks) + run.failed_tasks
        run.progress_stage = "replaying"
        run.error_log = json.dumps(errors, ensure_ascii=False)
        db.commit()

        calibrator = WalkForwardCalibrator()
        _seed_calibrator(db, calibrator, run.start_date)
        model_version = RuleBasedPredictionModel.version
        scoring_weights = load_scoring_weights(db)
        processed_tasks = 0
        for prediction_date, date_tasks_iter in groupby(tasks, key=lambda item: item[0]):
            pending_calibration_updates: list[tuple[float, str, str, bool | None]] = []
            for _, stock_id, _index in list(date_tasks_iter):
                stock = db.get(Stock, stock_id)
                frame = stock_frames[stock_id]
                run.current_ticker = stock.ticker if stock else str(stock_id)
                run.current_date = prediction_date
                try:
                    existing = db.scalar(
                        select(PredictionResult).where(
                            PredictionResult.stock_id == stock_id,
                            PredictionResult.prediction_date == prediction_date,
                            PredictionResult.horizon_days == run.horizon_days,
                            PredictionResult.prediction_source == "historical_replay",
                            PredictionResult.model_version == model_version,
                        )
                    )
                    if existing and not run.force_rebuild:
                        pending_calibration_updates.append(
                            (
                                existing.raw_up_probability or existing.up_probability,
                                stock.market,
                                existing.actual_direction or "flat",
                                existing.is_correct,
                            )
                        )
                        run.completed_tasks += 1
                        processed_tasks += 1
                        continue

                    prediction = build_prediction_for_date(
                        db,
                        stock,
                        frame,
                        prediction_date,
                        indicators_ready=True,
                        historical_context=contexts[stock_id],
                        weights=scoring_weights,
                    )
                    raw_probability = prediction["raw_up_probability"]
                    calibrated, calibration_samples, observed_up_rate = calibrator.calibrate(
                        raw_probability,
                        stock.market,
                    )
                    target_date, actual_return = next_trading_outcome(
                        frame,
                        prediction_date,
                        run.horizon_days,
                    )
                    actual_direction = direction_for_return(actual_return)
                    is_correct = direction_hit(calibrated, actual_return)
                    confidence = calibrator.confidence(
                        stock.market,
                        prediction["confidence_level"],
                    )
                    values = {
                        "target_date": target_date,
                        "final_score": prediction["final_score"],
                        "up_probability": calibrated,
                        "down_probability": round(100 - calibrated, 1),
                        "expected_range_low": prediction["expected_range_low"],
                        "expected_range_high": prediction["expected_range_high"],
                        "confidence_level": confidence,
                        "model_version": model_version,
                        "prediction_source": "historical_replay",
                        "replay_run_id": run.id,
                        "raw_up_probability": raw_probability,
                        "calibrated_up_probability": calibrated,
                        "actual_return": round(actual_return, 3),
                        "is_correct": is_correct,
                        "range_hit": range_hit_for_return(
                            prediction["expected_range_low"],
                            prediction["expected_range_high"],
                            actual_return,
                        ),
                        "actual_direction": actual_direction,
                        "absolute_error": absolute_forecast_error(
                            prediction["expected_range_low"],
                            prediction["expected_range_high"],
                            actual_return,
                        ),
                        "data_quality_note": prediction["data_quality_note"],
                        "historical_news_available": prediction[
                            "historical_news_available"
                        ],
                        "historical_financial_available": prediction[
                            "historical_financial_available"
                        ],
                        "feature_snapshot": json.dumps(
                            prediction["feature_snapshot"]
                            | {
                                "calibration_samples": calibration_samples,
                                "observed_up_rate": observed_up_rate,
                            },
                            ensure_ascii=False,
                        ),
                    }
                    if existing:
                        for key, value in values.items():
                            setattr(existing, key, value)
                    else:
                        db.add(
                            PredictionResult(
                                stock_id=stock_id,
                                prediction_date=prediction_date,
                                horizon_days=run.horizon_days,
                                **values,
                            )
                        )
                    pending_calibration_updates.append(
                        (
                            raw_probability,
                            stock.market,
                            actual_direction,
                            is_correct,
                        )
                    )
                    run.completed_tasks += 1
                except Exception as exc:
                    run.failed_tasks += 1
                    errors.append(
                        {
                            "ticker": stock.ticker if stock else str(stock_id),
                            "date": prediction_date.isoformat(),
                            "error": str(exc),
                        }
                    )
                    logger.exception(
                        "Historical replay failed for %s on %s",
                        stock.ticker if stock else stock_id,
                        prediction_date,
                    )
                processed_tasks += 1

            # D+1 outcomes become calibration evidence only after every prediction
            # for date D has been produced.
            for raw_probability, market, actual_direction, is_correct in pending_calibration_updates:
                calibrator.update(
                    raw_probability,
                    market,
                    actual_direction,
                    is_correct,
                )
            if processed_tasks % 50 == 0 or processed_tasks == len(tasks):
                run.error_log = json.dumps(errors[-100:], ensure_ascii=False)
                db.commit()

        run.status = "completed"
        run.progress_stage = "completed"
        run.current_ticker = None
        run.current_date = None
        run.completed_at = _utcnow()
        run.error_log = json.dumps(errors[-100:], ensure_ascii=False)
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(HistoricalReplayRun, run.id)
        if run:
            errors.append({"error": str(exc)})
            run.status = "failed"
            run.progress_stage = "failed"
            run.completed_at = _utcnow()
            run.error_log = json.dumps(errors[-100:], ensure_ascii=False)
            db.commit()
        logger.exception("Historical replay run %s failed", run.id if run else "unknown")


def _run_in_background(run_id: int) -> None:
    with SessionLocal() as db:
        run = db.get(HistoricalReplayRun, run_id)
        if run:
            run_historical_replay(db, run)


def create_replay_run(
    db: Session,
    *,
    lookback_years: int = 2,
    markets: list[str] | None = None,
    scope: str = "current_analysis_universe",
    horizon_days: int = 1,
    force_rebuild: bool = False,
    as_of_date: date | None = None,
) -> HistoricalReplayRun:
    today = as_of_date or date.today()
    run = HistoricalReplayRun(
        start_date=today - timedelta(days=365 * lookback_years),
        end_date=today,
        market_scope=",".join(markets or ["KR", "US"]),
        stock_scope=scope,
        horizon_days=horizon_days,
        force_rebuild=force_rebuild,
        status="queued",
        progress_stage="queued",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    _executor.submit(_run_in_background, run.id)
    return run


def serialize_replay_run(run: HistoricalReplayRun) -> dict:
    processed = run.completed_tasks + run.failed_tasks
    try:
        errors = json.loads(run.error_log or "[]")
    except json.JSONDecodeError:
        errors = []
    return {
        "id": run.id,
        "start_date": run.start_date,
        "end_date": run.end_date,
        "market_scope": run.market_scope.split(",") if run.market_scope else [],
        "stock_scope": run.stock_scope,
        "horizon_days": run.horizon_days,
        "status": run.status,
        "stage": run.progress_stage,
        "total_tasks": run.total_tasks,
        "completed_tasks": run.completed_tasks,
        "failed_tasks": run.failed_tasks,
        "processed_tasks": processed,
        "current_ticker": run.current_ticker,
        "current_date": run.current_date,
        "progress_percent": (
            round(min(100, processed / run.total_tasks * 100), 1)
            if run.total_tasks
            else 0
        ),
        "errors": errors,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }
