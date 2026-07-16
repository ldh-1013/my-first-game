from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from time import struct_time
from typing import Callable

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    DailyPrice,
    DailyReport,
    NewsArticle,
    NewsStockLink,
    PredictionResult,
    Recommendation,
    SentimentScore,
    Stock,
)
from app.feature_engineering.point_in_time import live_point_in_time_features
from app.services.financial_service import collect_financial_snapshot
from app.services.news_collector import fetch_news_for_ticker
from app.services.market_screener_service import discover_market_candidates
from app.services.ml_model_service import (
    confidence_from_active_model,
    live_feature_record,
    predict_with_active_model,
    selective_signal_decision,
)
from app.services.prediction_engine import RuleBasedPredictionModel
from app.services.price_collector import fetch_daily_prices
from app.services.quality_service import (
    data_quality_score,
    calibrated_probability,
    confidence_from_history,
    decision_status,
    financial_score,
    load_scoring_weights,
    surge_status,
)
from app.services.recommendation_engine import SAMPLE_UNIVERSE, select_candidates
from app.services.report_generator import build_report_content
from app.services.scoring_engine import (
    calculate_final_score,
    calculate_risk_score,
    calculate_technical_score,
    calculate_volume_score,
)
from app.services.sentiment_analyzer import aggregate_sentiment, analyze_sentiment
from app.services.technical_indicator import calculate_indicators
from app.utils.logger import get_logger

logger = get_logger(__name__)
ProgressCallback = Callable[[int, int, str, list[dict]], bool]


def _safe_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _to_datetime(value) -> datetime | None:
    if isinstance(value, struct_time):
        return datetime(*value[:6])
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return None


def normalize_ticker(ticker: str, market: str | None = None) -> str:
    normalized = ticker.strip().upper()
    if market == "KR" and normalized.isdigit() and len(normalized) == 6:
        return f"{normalized}.KS"
    return normalized


def _ensure_stock(db: Session, item: dict) -> Stock:
    ticker = normalize_ticker(item["ticker"], item.get("market") or item.get("market_type"))
    stock = db.scalar(select(Stock).where(Stock.ticker == ticker))
    if stock:
        if item.get("name"):
            stock.name = item["name"]
        return stock
    is_private = item.get("asset_type") == "PRIVATE"
    market = item.get("market") or item.get("market_type") or "US"
    stock = Stock(
        ticker=ticker,
        name=item.get("name") or ticker,
        market=market,
        country="KR" if market == "KR" else "US",
        asset_type=item.get("asset_type", "LISTED_STOCK"),
        is_listed=not is_private,
        currency=item.get("currency") or ("KRW" if market == "KR" else "USD"),
        data_source="unavailable" if is_private else "yfinance",
    )
    db.add(stock)
    db.flush()
    return stock


def _save_prices(db: Session, stock: Stock, frame: pd.DataFrame) -> None:
    for index, row in frame.tail(365).iterrows():
        row_date = pd.Timestamp(index).date()
        existing = db.scalar(
            select(DailyPrice).where(DailyPrice.stock_id == stock.id, DailyPrice.date == row_date)
        )
        close_value = _safe_float(row.get("close"))
        volume_value = _safe_float(row.get("volume"))
        values = {
            "open_price": _safe_float(row.get("open")),
            "high_price": _safe_float(row.get("high")),
            "low_price": _safe_float(row.get("low")),
            "close_price": close_value,
            "adjusted_close": _safe_float(row.get("adjusted_close")),
            "volume": volume_value,
            "trading_value": close_value * volume_value
            if close_value is not None and volume_value is not None
            else None,
            "change_rate": _safe_float(row.get("change_rate")),
            "ma5": _safe_float(row.get("ma5")),
            "ma20": _safe_float(row.get("ma20")),
            "ma60": _safe_float(row.get("ma60")),
            "rsi": _safe_float(row.get("rsi")),
            "atr": _safe_float(row.get("atr")),
            "volatility_20d": _safe_float(row.get("volatility_20d")),
            "volume_change_rate": _safe_float(row.get("volume_change_rate")),
        }
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
        else:
            db.add(DailyPrice(stock_id=stock.id, date=row_date, **values))


def _save_news(db: Session, stock: Stock, articles: list[dict]) -> list[dict]:
    results = []
    seen_hashes: set[str] = set()
    for article in articles:
        if article["content_hash"] in seen_hashes:
            continue
        seen_hashes.add(article["content_hash"])
        translated_text = (
            f"{article.get('translated_title', '')} {article.get('translated_summary', '')}"
        )
        result = analyze_sentiment(
            article["title"],
            article.get("summary", ""),
            translated_text,
        )
        result |= {
            "title": article.get("translated_title") or article["title"],
            "original_title": article["title"],
            "summary": article.get("translated_summary") or article.get("summary", ""),
            "source": article.get("source"),
        }
        results.append(result)
        news = db.scalar(
            select(NewsArticle).where(NewsArticle.content_hash == article["content_hash"])
        )
        if not news:
            news = NewsArticle(
                title=article["title"],
                summary=article.get("summary"),
                translated_title=article.get("translated_title"),
                translated_summary=article.get("translated_summary"),
                source=article.get("source"),
                url=article["url"],
                published_at=_to_datetime(article.get("published_at")),
                language="ko"
                if any("\uac00" <= char <= "\ud7a3" for char in article["title"])
                else "en",
                related_stock_id=stock.id,
                content_hash=article["content_hash"],
            )
            db.add(news)
            db.flush()
        else:
            if article.get("translated_title"):
                news.translated_title = article["translated_title"]
            if article.get("translated_summary"):
                news.translated_summary = article["translated_summary"]
        link = db.scalar(
            select(NewsStockLink).where(
                NewsStockLink.article_id == news.id,
                NewsStockLink.stock_id == stock.id,
            )
        )
        if not link:
            db.add(NewsStockLink(article_id=news.id, stock_id=stock.id))
        sentiment = db.scalar(
            select(SentimentScore).where(
                SentimentScore.article_id == news.id,
                SentimentScore.stock_id == stock.id,
            )
        )
        if not sentiment:
            sentiment = SentimentScore(article_id=news.id, stock_id=stock.id)
            db.add(sentiment)
        sentiment.sentiment_label = result["sentiment_label"]
        sentiment.sentiment_score = result["sentiment_score"]
        sentiment.short_term_impact = result["short_term_impact"]
        sentiment.long_term_impact = result["long_term_impact"]
        sentiment.confidence = result["confidence"]
        sentiment.model_name = "weighted-news-v3"
    return results


def _latest_as_dict(frame: pd.DataFrame) -> dict | None:
    if frame.empty:
        return None
    row = frame.iloc[-1]
    return {key: _safe_float(value) for key, value in row.items()}


def _load_stored_prices(db: Session, stock: Stock) -> pd.DataFrame:
    rows = db.scalars(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id)
        .order_by(DailyPrice.date.asc())
    ).all()
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
                "change_rate": row.change_rate,
                "ma5": row.ma5,
                "ma20": row.ma20,
                "ma60": row.ma60,
                "rsi": row.rsi,
                "atr": row.atr,
                "volatility_20d": row.volatility_20d,
                "volume_change_rate": row.volume_change_rate,
            }
            for row in rows
        ],
        index=pd.to_datetime([row.date for row in rows]),
    )


def analyze_stock(db: Session, stock: Stock) -> dict:
    raw_prices = fetch_daily_prices(stock.ticker)
    prices = calculate_indicators(raw_prices) if not raw_prices.empty else raw_prices
    if not prices.empty:
        _save_prices(db, stock, prices)
        db.flush()
    else:
        prices = _load_stored_prices(db, stock)

    articles = fetch_news_for_ticker(stock.ticker, stock.name)
    sentiments = _save_news(db, stock, articles)
    latest = _latest_as_dict(prices)
    snapshot = collect_financial_snapshot(db, stock) if latest else None

    news_score = aggregate_sentiment(sentiments)
    technical_score = calculate_technical_score(latest)
    volume_score = calculate_volume_score(latest)
    finance_score = financial_score(snapshot)
    risk_score = calculate_risk_score(latest, bool(sentiments), stock.is_listed)
    final_score = calculate_final_score(
        news_score=news_score,
        technical_score=technical_score,
        volume_score=volume_score,
        financial_score=finance_score,
        risk_score=risk_score,
        weights=load_scoring_weights(db),
    )
    baseline_prediction = RuleBasedPredictionModel().predict(
        final_score=final_score,
        volatility=latest.get("volatility_20d") if latest else None,
        data_points=len(prices),
    )
    as_of_date = (
        pd.Timestamp(prices.index[-1]).date()
        if not prices.empty
        else date.today()
    )
    point_features = live_point_in_time_features(
        db,
        stock_id=stock.id,
        market=stock.market,
        as_of_date=as_of_date,
    )
    ml_features = live_feature_record(
        technical_score=technical_score,
        volume_score=volume_score,
        news_score=news_score,
        financial_score=finance_score,
        risk_score=risk_score,
        final_score=final_score,
        latest=latest,
        price_rows=len(prices),
        news_available=bool(sentiments),
        financial_available=snapshot is not None,
        market=stock.market,
        point_in_time_features=point_features,
    )
    prediction = predict_with_active_model(
        db,
        live_features=ml_features,
        baseline_prediction=baseline_prediction,
    )
    active_model = prediction.pop("active_model")
    raw_up_probability = prediction.pop("raw_up_probability")
    model_calibrated_probability = prediction.pop(
        "model_calibrated_probability",
        None,
    )
    quality = data_quality_score(
        price_rows=len(prices),
        latest_price=latest.get("close") if latest else None,
        news_count=len(sentiments),
        has_financials=snapshot is not None,
    )
    prediction["up_probability"] = (
        model_calibrated_probability
        if active_model.model_type != "baseline"
        else calibrated_probability(
            db,
            raw_up_probability,
            market=stock.market,
        )
    )
    prediction["down_probability"] = round(100 - prediction["up_probability"], 1)
    if active_model.model_type == "baseline":
        confidence = confidence_from_history(
            db,
            market=stock.market,
            raw_probability=raw_up_probability,
            base_confidence=prediction["confidence_level"],
            data_quality=quality,
            volatility=latest.get("volatility_20d") if latest else None,
            news_available=bool(sentiments),
            financial_available=snapshot is not None,
        )
    else:
        confidence = confidence_from_active_model(
            active_model,
            probability=prediction["up_probability"],
            base_confidence=prediction["confidence_level"],
            data_quality=quality,
            volatility=latest.get("volatility_20d") if latest else None,
            news_available=bool(sentiments),
            financial_available=snapshot is not None,
        )
    prediction["confidence_level"] = confidence["level"]
    surge_warning, surge_reason = surge_status(latest)
    status = decision_status(
        quality,
        prediction["confidence_level"],
        prediction["up_probability"],
        final_score,
    )
    selective_signal = selective_signal_decision(
        active_model,
        probability=prediction["up_probability"],
        data_quality=quality,
        liquidity_percentile=_safe_float(point_features.get("liquidity_percentile")),
        volatility=latest.get("volatility_20d") if latest else None,
    )
    if selective_signal["status"] == "defer":
        status = "defer"
    if status == "defer":
        prediction["confidence_level"] = (
            "very_low"
            if prediction["confidence_level"] == "very_low"
            else "low"
        )
    content = build_report_content(
        stock_name=stock.name,
        latest=latest,
        sentiment_results=sentiments,
        risk_score=risk_score,
        prediction=prediction,
    )

    db.execute(
        delete(DailyReport).where(
            DailyReport.stock_id == stock.id,
            DailyReport.report_date == date.today(),
        )
    )
    recent_return = float(latest.get("recent_5d_return") or 0) if latest else 0
    report = DailyReport(
        stock_id=stock.id,
        report_date=date.today(),
        current_price=latest.get("close") if latest else None,
        change_rate=latest.get("change_rate") if latest else None,
        recent_5d_flow="상승" if recent_return > 0 else "하락" if latest else "data_unavailable",
        volume_change=latest.get("volume_change_rate") if latest else None,
        positive_factors=json.dumps(content["positive_factors"], ensure_ascii=False),
        negative_factors=json.dumps(content["negative_factors"], ensure_ascii=False),
        neutral_factors=json.dumps(content["neutral_factors"], ensure_ascii=False),
        news_summary=content["news_summary"],
        technical_analysis=content["technical_analysis"],
        flow_analysis=content["flow_analysis"],
        macro_industry_summary=(
            "무료 데이터 기준 재무·가격·뉴스를 통합했습니다. 거시경제 데이터는 참고 수준입니다."
        ),
        up_probability=prediction["up_probability"],
        down_probability=prediction["down_probability"],
        expected_range_low=prediction["expected_range_low"],
        expected_range_high=prediction["expected_range_high"],
        confidence_level=prediction["confidence_level"],
        key_risks=content["key_risks"],
        user_checklist=content["user_checklist"],
        final_view=content["final_view"] if status != "defer" else "데이터 부족 · 판단 보류",
        final_score=final_score,
        data_quality_score=quality,
        decision_status=status,
        surge_warning=surge_warning,
        surge_reason=surge_reason,
        active_model_version=prediction["model_version"],
        raw_up_probability=raw_up_probability,
        calibrated_up_probability=prediction["up_probability"],
        validation_sample_count=confidence["sample_count"],
        probability_bucket_observed_rate=confidence["calibration"].get(
            "observed_up_rate"
        ),
        confidence_basis=json.dumps(confidence["reasons"], ensure_ascii=False),
        market_regime=str(point_features.get("market_regime", "sideways_low_vol")),
        signal_status=selective_signal["status"],
        defer_reason=" ".join(selective_signal["reasons"]),
    )
    db.add(report)
    existing_prediction = db.scalar(
        select(PredictionResult).where(
            PredictionResult.stock_id == stock.id,
            PredictionResult.prediction_date == date.today(),
            PredictionResult.horizon_days == 1,
            PredictionResult.prediction_source == "live",
        )
    )
    prediction_values = {
        "final_score": final_score,
        "up_probability": prediction["up_probability"],
        "down_probability": prediction["down_probability"],
        "expected_range_low": prediction["expected_range_low"],
        "expected_range_high": prediction["expected_range_high"],
        "confidence_level": prediction["confidence_level"],
        "model_version": prediction["model_version"],
        "prediction_source": "live",
        "raw_up_probability": raw_up_probability,
        "calibrated_up_probability": prediction["up_probability"],
        "data_quality_note": (
            "live_complete"
            if latest and sentiments and snapshot
            else "incomplete"
        ),
        "historical_news_available": False,
        "historical_financial_available": False,
        "market_regime": str(point_features.get("market_regime", "sideways_low_vol")),
        "signal_status": selective_signal["status"],
        "defer_reason": " ".join(selective_signal["reasons"]),
        "feature_snapshot": json.dumps(
            {
                **ml_features,
                "selective_signal": selective_signal,
                "calibration": confidence["calibration"],
                "confidence_score": confidence["score"],
                "confidence_reasons": confidence["reasons"],
                "data_quality_score": quality,
            },
            ensure_ascii=False,
        ),
    }
    if existing_prediction:
        for key, value in prediction_values.items():
            setattr(existing_prediction, key, value)
    else:
        db.add(
            PredictionResult(
                stock_id=stock.id,
                prediction_date=date.today(),
                horizon_days=1,
                **prediction_values,
            )
        )
    db.flush()
    return {
        "report": report,
        "stock": stock,
        "final_score": final_score,
        "confidence_level": prediction["confidence_level"],
    }


def build_analysis_universe(
    holdings: list,
    *,
    include_recommendations: bool = True,
    include_holdings: bool = True,
) -> list[dict]:
    universe: dict[str, dict] = {}
    if include_holdings:
        for holding in holdings:
            universe[holding.stock.ticker] = {
                "ticker": holding.stock.ticker,
                "name": holding.stock.name,
                "market": holding.market_type,
                "currency": holding.currency,
                "asset_type": holding.asset_type,
            }
    if include_recommendations:
        for item in SAMPLE_UNIVERSE:
            universe.setdefault(item["ticker"], item)
        for item in discover_market_candidates():
            universe.setdefault(item["ticker"], item)
    return list(universe.values())


def run_analysis_items(
    db: Session,
    items: list[dict],
    *,
    include_recommendations: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    results, errors = [], []
    cancelled = False
    for item in items:
        if progress_callback and progress_callback(len(results), len(errors), item["ticker"], errors):
            cancelled = True
            break
        try:
            stock = _ensure_stock(db, item)
            results.append(analyze_stock(db, stock))
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.exception("Analysis failed for %s", item["ticker"])
            errors.append({"ticker": item["ticker"], "error": str(exc)})
        if progress_callback and progress_callback(
            len(results),
            len(errors),
            item["ticker"],
            errors,
        ):
            cancelled = True
            break

    if include_recommendations and not cancelled:
        db.execute(delete(Recommendation).where(Recommendation.report_date == date.today()))
        for rank, result in enumerate(select_candidates(results, limit=5), start=1):
            report, stock = result["report"], result["stock"]
            db.add(
                Recommendation(
                    report_date=date.today(),
                    stock_id=stock.id,
                    rank=rank,
                    total_score=report.final_score,
                    up_probability=report.up_probability,
                    expected_range_low=report.expected_range_low,
                    expected_range_high=report.expected_range_high,
                    reason=(
                        f"{report.final_view} · 상승 가능성 {report.up_probability:.1f}% · "
                        f"종합 점수 {report.final_score:.1f}"
                    ),
                    risk_summary=report.key_risks,
                    time_horizon="DAY 1~2 관찰",
                    checklist=report.user_checklist,
                    surge_warning=report.surge_warning,
                    surge_reason=report.surge_reason,
                )
            )
        db.commit()
    return {
        "success": bool(results),
        "message": "analysis completed" if results else "analysis completed with no results",
        "analyzed": len(results),
        "failed": len(errors),
        "errors": errors,
        "cancelled": cancelled,
    }


def run_analysis(
    db: Session,
    holdings: list,
    include_recommendations: bool = True,
    include_holdings: bool = True,
) -> dict:
    return run_analysis_items(
        db,
        build_analysis_universe(
            holdings,
            include_recommendations=include_recommendations,
            include_holdings=include_holdings,
        ),
        include_recommendations=include_recommendations,
    )
