from __future__ import annotations

import json
import math
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyPrice, PredictionResult, Stock
from app.services.prediction_engine import RuleBasedPredictionModel
from app.services.quality_service import load_scoring_weights
from app.services.scoring_engine import calculate_final_score


def direction_for_return(actual_return: float) -> str:
    if actual_return > 0:
        return "up"
    if actual_return < 0:
        return "down"
    return "flat"


def direction_hit(up_probability: float, actual_return: float) -> bool | None:
    direction = direction_for_return(actual_return)
    if direction == "flat":
        return None
    return (up_probability >= 50) == (direction == "up")


def range_hit_for_return(low: float, high: float, actual_return: float) -> bool:
    return low <= actual_return <= high


def absolute_forecast_error(low: float, high: float, actual_return: float) -> float:
    midpoint = (low + high) / 2
    return round(abs(actual_return - midpoint), 3)


def settle_predictions(db: Session) -> int:
    """Settle live predictions only; replay rows are settled when they are created."""
    pending = db.scalars(
        select(PredictionResult).where(
            PredictionResult.actual_return.is_(None),
            PredictionResult.prediction_source == "live",
        )
    ).all()
    settled = 0
    for prediction in pending:
        base = db.scalar(
            select(DailyPrice)
            .where(
                DailyPrice.stock_id == prediction.stock_id,
                DailyPrice.date <= prediction.prediction_date,
                DailyPrice.close_price.is_not(None),
            )
            .order_by(DailyPrice.date.desc())
        )
        target_rows = db.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_id == prediction.stock_id,
                DailyPrice.date > prediction.prediction_date,
                DailyPrice.close_price.is_not(None),
            )
            .order_by(DailyPrice.date.asc())
            .limit(max(1, prediction.horizon_days))
        ).all()
        if not base or len(target_rows) < prediction.horizon_days:
            continue
        target = target_rows[prediction.horizon_days - 1]
        if not base.close_price or target.close_price is None:
            continue
        actual = (target.close_price / base.close_price - 1) * 100
        probability = prediction.calibrated_up_probability or prediction.up_probability
        prediction.actual_return = round(actual, 3)
        prediction.target_date = target.date
        prediction.actual_direction = direction_for_return(actual)
        prediction.is_correct = direction_hit(probability, actual)
        prediction.range_hit = range_hit_for_return(
            prediction.expected_range_low,
            prediction.expected_range_high,
            actual,
        )
        prediction.absolute_error = absolute_forecast_error(
            prediction.expected_range_low,
            prediction.expected_range_high,
            actual,
        )
        settled += 1
    if settled:
        db.commit()
    return settled


def _rate(rows: list[PredictionResult], attribute: str) -> float | None:
    values = [getattr(row, attribute) for row in rows if getattr(row, attribute) is not None]
    if not values:
        return None
    return round(sum(1 for value in values if value) / len(values) * 100, 1)


def _accuracy(rows: list[PredictionResult]) -> float | None:
    return _rate(rows, "is_correct")


def _normalized_weights(weights: dict[str, float]) -> dict[str, float]:
    result = weights.copy()
    positive_keys = ["news", "technical", "volume", "financial", "industry_macro"]
    total = sum(max(0, result.get(key, 0)) for key in positive_keys) or 1
    for key in positive_keys:
        result[key] = max(0, result.get(key, 0)) / total
    result["risk_penalty"] = max(0, min(0.5, result.get("risk_penalty", 0.08)))
    return result


def _candidate_weights(base: dict[str, float]) -> list[tuple[str, dict[str, float]]]:
    variations = [("운영 가중치", base.copy())]
    for name, changes in [
        ("기술 지표 강화", {"technical": 0.10, "news": -0.05, "financial": -0.05}),
        ("거래량 강화", {"volume": 0.10, "news": -0.05, "financial": -0.05}),
        (
            "가격 신호 균형 강화",
            {"technical": 0.06, "volume": 0.06, "news": -0.06, "financial": -0.06},
        ),
        ("리스크 감점 강화", {"risk_penalty": 0.04}),
    ]:
        candidate = base.copy()
        for key, delta in changes.items():
            candidate[key] = candidate.get(key, 0) + delta
        variations.append((name, _normalized_weights(candidate)))
    return [(name, _normalized_weights(weights)) for name, weights in variations]


def _features(row: PredictionResult) -> dict | None:
    try:
        values = json.loads(row.feature_snapshot or "{}")
    except json.JSONDecodeError:
        return None
    required = {"technical_score", "volume_score", "news_score", "financial_score", "risk_score"}
    return values if required.issubset(values) else None


def _candidate_accuracy(
    rows: list[tuple[PredictionResult, dict]],
    weights: dict[str, float],
) -> float | None:
    outcomes: list[bool] = []
    for row, features in rows:
        if row.actual_direction not in {"up", "down"}:
            continue
        final_score = calculate_final_score(
            news_score=float(features["news_score"]),
            technical_score=float(features["technical_score"]),
            volume_score=float(features["volume_score"]),
            financial_score=float(features["financial_score"]),
            risk_score=float(features["risk_score"]),
            weights=weights,
        )
        predicted_up = RuleBasedPredictionModel.score_to_probability(final_score) >= 0.5
        outcomes.append(predicted_up == (row.actual_direction == "up"))
    return sum(outcomes) / len(outcomes) * 100 if outcomes else None


def _baseline_accuracy(rows: list[tuple[PredictionResult, dict]]) -> float | None:
    outcomes = [
        ((row.raw_up_probability or row.up_probability) >= 50)
        == (row.actual_direction == "up")
        for row, _ in rows
        if row.actual_direction in {"up", "down"}
    ]
    return sum(outcomes) / len(outcomes) * 100 if outcomes else None


def _correlation(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 20:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys)
    )
    return round(numerator / denominator, 3) if denominator else None


def candidate_model_summary(db: Session, rows: list[PredictionResult]) -> dict:
    featured = [(row, values) for row in rows if (values := _features(row))]
    if len(featured) < 200:
        return {
            "status": "insufficient",
            "message": "훈련·검증 구간을 분리할 과거 재현 표본이 부족합니다.",
            "training_samples": 0,
            "validation_samples": 0,
            "applied": False,
            "component_performance": {},
        }
    ordered = sorted(featured, key=lambda item: item[0].prediction_date)
    split_date = ordered[0][0].prediction_date + timedelta(days=456)
    training = [item for item in ordered if item[0].prediction_date < split_date]
    validation = [item for item in ordered if item[0].prediction_date >= split_date]
    if len(training) < 100 or len(validation) < 100:
        return {
            "status": "insufficient",
            "message": "앞 15개월 훈련·뒤 9개월 검증에 필요한 표본이 부족합니다.",
            "training_samples": len(training),
            "validation_samples": len(validation),
            "applied": False,
            "component_performance": {},
        }

    base = load_scoring_weights(db)
    candidates = _candidate_weights(base)
    scored = [
        (name, weights, _candidate_accuracy(training, weights))
        for name, weights in candidates
    ]
    best_name, best_weights, best_training = max(
        scored,
        key=lambda item: item[2] if item[2] is not None else -1,
    )
    baseline_validation = _baseline_accuracy(validation)
    candidate_validation = _candidate_accuracy(validation, best_weights)
    improved = (
        best_name != "운영 가중치"
        and baseline_validation is not None
        and candidate_validation is not None
        and candidate_validation >= baseline_validation + 1.0
    )
    component_performance = {
        key: _correlation(
            [
                (float(features[key]), float(row.actual_return))
                for row, features in validation
                if row.actual_return is not None
            ]
        )
        for key in [
            "news_score",
            "technical_score",
            "volume_score",
            "financial_score",
            "risk_score",
        ]
    }
    return {
        "status": "candidate" if improved else "not_improved",
        "message": (
            "분리된 검증 구간에서도 개선되어 후보 모델로 표시합니다."
            if improved
            else "훈련 구간 후보가 별도 검증 구간에서 의미 있게 개선되지 않았습니다."
        ),
        "name": best_name,
        "weights": {key: round(value, 4) for key, value in best_weights.items()},
        "training_accuracy": round(best_training, 1) if best_training is not None else None,
        "baseline_validation_accuracy": (
            round(baseline_validation, 1) if baseline_validation is not None else None
        ),
        "candidate_validation_accuracy": (
            round(candidate_validation, 1) if candidate_validation is not None else None
        ),
        "training_samples": len(training),
        "validation_samples": len(validation),
        "applied": False,
        "component_performance": component_performance,
    }


def backtest_summary(
    db: Session,
    stock_id: int | None = None,
    replay_run_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    markets: list[str] | None = None,
) -> dict:
    settle_predictions(db)
    statement = select(PredictionResult).where(
        PredictionResult.prediction_source == "historical_replay",
        PredictionResult.model_version == RuleBasedPredictionModel.version,
        PredictionResult.actual_return.is_not(None),
    )
    if stock_id is not None:
        statement = statement.where(PredictionResult.stock_id == stock_id)
    if replay_run_id is not None:
        statement = statement.where(PredictionResult.replay_run_id == replay_run_id)
    if start_date is not None:
        statement = statement.where(PredictionResult.prediction_date >= start_date)
    if end_date is not None:
        statement = statement.where(PredictionResult.prediction_date <= end_date)
    if markets:
        statement = statement.join(Stock, Stock.id == PredictionResult.stock_id).where(
            Stock.market.in_(markets)
        )
    rows = list(
        db.scalars(statement.order_by(PredictionResult.prediction_date.desc())).all()
    )
    total = len(rows)
    direction_rows = [row for row in rows if row.is_correct is not None]
    errors = [row.absolute_error for row in rows if row.absolute_error is not None]
    recent_cutoff = date.today() - timedelta(days=92)
    two_year_cutoff = date.today() - timedelta(days=730)
    recent_rows = [row for row in rows if row.prediction_date >= recent_cutoff]
    two_year_rows = [row for row in rows if row.prediction_date >= two_year_cutoff]
    details = []
    for row in rows[:250]:
        stock = db.get(Stock, row.stock_id)
        details.append(
            {
                "ticker": stock.ticker if stock else str(row.stock_id),
                "name": stock.name if stock else "",
                "market": stock.market if stock else "",
                "prediction_date": row.prediction_date,
                "target_date": row.target_date,
                "up_probability": row.raw_up_probability or row.up_probability,
                "calibrated_up_probability": (
                    row.calibrated_up_probability or row.up_probability
                ),
                "expected_range_low": row.expected_range_low,
                "expected_range_high": row.expected_range_high,
                "actual_return": row.actual_return,
                "actual_direction": row.actual_direction,
                "is_correct": row.is_correct,
                "range_hit": row.range_hit,
                "absolute_error": row.absolute_error,
                "horizon_days": row.horizon_days,
                "data_quality_note": row.data_quality_note,
                "historical_news_available": row.historical_news_available,
                "historical_financial_available": row.historical_financial_available,
            }
        )
    accuracy = _accuracy(direction_rows)
    return {
        "evaluated": total,
        "direction_evaluated": len(direction_rows),
        "correct": sum(1 for row in direction_rows if row.is_correct),
        "accuracy": accuracy,
        "mean_absolute_error": (
            round(sum(errors) / len(errors), 2) if errors else None
        ),
        "range_accuracy": _rate(rows, "range_hit"),
        "recent_3m_accuracy": _accuracy(recent_rows),
        "recent_2y_accuracy": _accuracy(two_year_rows),
        "status": "ready" if total >= 100 else "collecting",
        "calibration_status": (
            "high_sample_review"
            if total >= 200
            else "reference_available"
            if total >= 100
            else "insufficient"
        ),
        "minimum_recommended_samples": 100,
        "high_confidence_review_samples": 200,
        "methodology": "historical_replay",
        "candidate_model": candidate_model_summary(db, rows),
        "details": details,
    }
