from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FinancialSnapshot, PredictionResult, Setting, Stock
from app.services.prediction_engine import RuleBasedPredictionModel


DEFAULT_WEIGHTS = {
    "news": 0.25,
    "technical": 0.25,
    "volume": 0.20,
    "financial": 0.20,
    "industry_macro": 0.10,
    "risk_penalty": 0.08,
}


def load_scoring_weights(db: Session) -> dict[str, float]:
    row = db.scalar(select(Setting).where(Setting.key == "scoring_weights"))
    if not row:
        return DEFAULT_WEIGHTS.copy()
    try:
        values = {key: float(value) for key, value in json.loads(row.value).items()}
    except (TypeError, ValueError, json.JSONDecodeError):
        return DEFAULT_WEIGHTS.copy()
    merged = DEFAULT_WEIGHTS | values
    positive_total = sum(merged[key] for key in ("news", "technical", "volume", "financial", "industry_macro"))
    if positive_total <= 0:
        return DEFAULT_WEIGHTS.copy()
    for key in ("news", "technical", "volume", "financial", "industry_macro"):
        merged[key] = merged[key] / positive_total
    merged["risk_penalty"] = max(0, min(0.5, merged["risk_penalty"]))
    return merged


def financial_score(snapshot: FinancialSnapshot | None) -> float:
    if not snapshot:
        return 0.0
    score = 0.0
    if snapshot.return_on_equity is not None:
        score += max(-25, min(25, snapshot.return_on_equity * 100))
    if snapshot.earnings_growth is not None:
        score += max(-25, min(25, snapshot.earnings_growth * 50))
    if snapshot.free_cash_flow is not None:
        score += 15 if snapshot.free_cash_flow > 0 else -15
    if snapshot.total_debt is not None and snapshot.market_cap:
        debt_ratio = snapshot.total_debt / snapshot.market_cap
        score += 15 if debt_ratio < 0.3 else -15 if debt_ratio > 0.8 else 0
    return round(max(-100, min(100, score)), 2)


def data_quality_score(
    *,
    price_rows: int,
    latest_price: float | None,
    news_count: int,
    has_financials: bool,
) -> float:
    score = min(40, price_rows / 60 * 40)
    score += 20 if latest_price is not None else 0
    score += min(20, news_count * 4)
    score += 20 if has_financials else 0
    return round(score, 1)


def surge_status(latest: dict | None) -> tuple[bool, str]:
    if not latest:
        return False, ""
    reasons: list[str] = []
    change = float(latest.get("change_rate") or 0)
    five_day = float(latest.get("recent_5d_return") or 0)
    volume = float(latest.get("volume_change_rate") or 0)
    if change >= 12:
        reasons.append(f"일간 상승률 {change:.1f}%")
    if five_day >= 20:
        reasons.append(f"최근 5거래일 상승률 {five_day:.1f}%")
    if volume >= 150:
        reasons.append(f"거래량 증가율 {volume:.0f}%")
    return bool(reasons), " · ".join(reasons)


def decision_status(quality: float, confidence: str, up_probability: float, final_score: float) -> str:
    if quality < 50 or confidence in {"low", "very_low"}:
        return "defer"
    if up_probability >= 62 and final_score >= 60:
        return "buy_watch"
    if up_probability <= 38 or final_score <= 40:
        return "risk_reduce"
    return "hold"


def _probability_bucket(raw_probability: float) -> tuple[float, float]:
    low = max(0.0, min(90.0, int(raw_probability // 10) * 10.0))
    return low, low + 10.0


def calibration_snapshot(
    db: Session,
    raw_probability: float,
    *,
    market: str | None = None,
    before_date: date | None = None,
) -> dict:
    low, high = _probability_bucket(raw_probability)
    conditions = [
        PredictionResult.prediction_source == "historical_replay",
        PredictionResult.model_version == RuleBasedPredictionModel.version,
        PredictionResult.actual_direction.in_(["up", "down"]),
        PredictionResult.raw_up_probability.is_not(None),
        PredictionResult.raw_up_probability >= low,
        PredictionResult.raw_up_probability < high,
    ]
    if before_date is not None:
        conditions.append(PredictionResult.prediction_date < before_date)

    global_rows = list(db.scalars(select(PredictionResult).where(*conditions)).all())
    market_rows: list[PredictionResult] = []
    if market:
        market_rows = list(
            db.scalars(
                select(PredictionResult)
                .join(Stock, Stock.id == PredictionResult.stock_id)
                .where(*conditions, Stock.market == market)
            ).all()
        )

    selected = market_rows.copy()
    if len(selected) < 50:
        selected_ids = {row.id for row in selected}
        selected.extend(row for row in global_rows if row.id not in selected_ids)
    selected = selected[:500]
    sample_count = len(selected)
    if not sample_count:
        return {
            "calibrated_probability": round(raw_probability, 1),
            "sample_count": 0,
            "observed_up_rate": None,
            "bucket_low": low,
            "bucket_high": high,
            "market_sample_count": 0,
        }

    up_count = sum(1 for row in selected if row.actual_direction == "up")
    prior_strength = 20.0
    prior_rate = raw_probability / 100
    posterior_rate = (up_count + prior_rate * prior_strength) / (
        sample_count + prior_strength
    )
    evidence_weight = sample_count / (sample_count + 100)
    calibrated_rate = prior_rate * (1 - evidence_weight) + posterior_rate * evidence_weight
    return {
        "calibrated_probability": round(
            max(5, min(95, calibrated_rate * 100)),
            1,
        ),
        "sample_count": sample_count,
        "observed_up_rate": round(up_count / sample_count * 100, 1),
        "bucket_low": low,
        "bucket_high": high,
        "market_sample_count": len(market_rows),
    }


def calibrated_probability(
    db: Session,
    raw_probability: float,
    market: str | None = None,
    before_date: date | None = None,
) -> float:
    return calibration_snapshot(
        db,
        raw_probability,
        market=market,
        before_date=before_date,
    )["calibrated_probability"]


def confidence_from_history(
    db: Session,
    *,
    market: str,
    raw_probability: float,
    base_confidence: str,
    data_quality: float,
    volatility: float | None,
    news_available: bool,
    financial_available: bool,
) -> dict:
    rows = list(
        db.scalars(
            select(PredictionResult)
            .join(Stock, Stock.id == PredictionResult.stock_id)
            .where(
                PredictionResult.prediction_source == "historical_replay",
                PredictionResult.model_version == RuleBasedPredictionModel.version,
                PredictionResult.actual_return.is_not(None),
                Stock.market == market,
            )
        ).all()
    )
    calibration = calibration_snapshot(db, raw_probability, market=market)
    directional = [row for row in rows if row.is_correct is not None]
    range_rows = [row for row in rows if row.range_hit is not None]
    errors = [row.absolute_error for row in rows if row.absolute_error is not None]
    recent_cutoff = date.today() - timedelta(days=92)
    recent = [
        row for row in directional if row.prediction_date >= recent_cutoff
    ]
    accuracy = (
        sum(1 for row in directional if row.is_correct) / len(directional) * 100
        if directional
        else None
    )
    recent_accuracy = (
        sum(1 for row in recent if row.is_correct) / len(recent) * 100
        if recent
        else None
    )
    range_accuracy = (
        sum(1 for row in range_rows if row.range_hit) / len(range_rows) * 100
        if range_rows
        else None
    )
    mae = sum(errors) / len(errors) if errors else None

    score = 0
    reasons: list[str] = []
    sample_count = len(rows)
    if sample_count < 30:
        score -= 4
        reasons.append("과거 재현 표본이 30건 미만입니다.")
    elif sample_count < 100:
        score -= 2
        reasons.append("과거 재현 표본이 최소 참고 기준 100건보다 적습니다.")
    elif sample_count >= 200:
        score += 1
        reasons.append(f"과거 재현 표본 {sample_count}건을 참고했습니다.")

    if accuracy is not None:
        if accuracy < 48:
            score -= 2
        elif accuracy < 53:
            score -= 1
        elif accuracy >= 58:
            score += 1
        reasons.append(f"시장별 방향 적중률 {accuracy:.1f}%")
    if recent_accuracy is not None:
        score += 1 if recent_accuracy >= 57 else -1 if recent_accuracy < 48 else 0
        reasons.append(f"최근 3개월 방향 적중률 {recent_accuracy:.1f}%")
    if mae is not None:
        score += 1 if mae < 1.5 else -2 if mae > 4 else -1 if mae > 2.5 else 0
        reasons.append(f"평균 절대오차 {mae:.2f}%p")
    if range_accuracy is not None:
        score += 1 if range_accuracy >= 65 else -1 if range_accuracy < 45 else 0
        reasons.append(f"예상 범위 적중률 {range_accuracy:.1f}%")

    score += 1 if data_quality >= 90 else -2 if data_quality < 60 else -1 if data_quality < 75 else 0
    if volatility is not None:
        score += 1 if volatility < 25 else -2 if volatility > 70 else -1 if volatility > 45 else 0
        reasons.append(f"현재 연환산 변동성 {volatility:.1f}%")
    if not news_available or not financial_available:
        score -= 1
        reasons.append("현재 뉴스·재무 데이터 중 일부가 제한적입니다.")

    if score >= 3:
        level = "high"
    elif score >= 0:
        level = "medium"
    elif score >= -3:
        level = "low"
    else:
        level = "very_low"
    if sample_count < 30:
        level = "very_low"
    elif sample_count < 100 and level in {"high", "medium"}:
        level = "low"
    if base_confidence == "low" and level in {"high", "medium"}:
        level = "low"
    return {
        "level": level,
        "score": score,
        "sample_count": sample_count,
        "calibration": calibration,
        "accuracy": round(accuracy, 1) if accuracy is not None else None,
        "recent_3m_accuracy": (
            round(recent_accuracy, 1) if recent_accuracy is not None else None
        ),
        "mean_absolute_error": round(mae, 2) if mae is not None else None,
        "range_accuracy": (
            round(range_accuracy, 1) if range_accuracy is not None else None
        ),
        "reasons": reasons,
    }
