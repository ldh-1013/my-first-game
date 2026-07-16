from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    mean_absolute_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ensemble.dynamic_ensemble import (
    combine_one,
    combine_probabilities,
    fit_regime_weights,
)
from app.evaluation.performance import (
    meaningful_move_metrics,
    select_confidence_threshold,
    selective_signal_metrics,
)
from app.feature_engineering.point_in_time import (
    POINT_IN_TIME_FEATURES,
    build_point_in_time_feature_map,
)
from app.models import (
    ModelActivationEvent,
    ModelExperiment,
    ModelVersion,
    PredictionResult,
    Stock,
)
from app.services.prediction_engine import RuleBasedPredictionModel

FEATURE_SET_VERSION = "point-in-time-market-regime-v2"
BASELINE_VERSION = RuleBasedPredictionModel.version
MIN_TRAIN_SAMPLES = 500
MIN_CALIBRATION_SAMPLES = 150
MIN_TEST_SAMPLES = 150
MODEL_DIR = Path(__file__).resolve().parents[2] / "data" / "models"

CORE_FEATURES = [
    "technical_score",
    "volume_score",
    "news_score",
    "financial_score",
    "risk_score",
    "final_score",
    "rsi",
    "volatility_20d",
    "price_rows",
    "historical_news_available",
    "historical_financial_available",
    "market_kr",
    "market_us",
]
OPTIONAL_FEATURES = [
    "recent_5d_return",
    "recent_20d_return",
    "ma5_gap",
    "ma20_gap",
    "macd",
    "atr",
    "volume_change_rate",
]
POINT_FEATURES = [
    key
    for key in POINT_IN_TIME_FEATURES
    if key not in set(CORE_FEATURES + OPTIONAL_FEATURES)
]
ALLOWED_SNAPSHOT_FEATURES = set(CORE_FEATURES + OPTIONAL_FEATURES) | {
    "close",
    "as_of_date",
    "mode",
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _json(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def _model_parameters(model: Pipeline) -> dict:
    return {
        key: value
        if isinstance(value, (str, int, float, bool, type(None)))
        else repr(value)
        for key, value in model.get_params(deep=True).items()
    }


def _finite(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if math.isfinite(number) else np.nan


def _feature_record(
    *,
    snapshot: dict,
    final_score: float,
    market: str,
    historical_news_available: bool,
    historical_financial_available: bool,
) -> dict[str, float]:
    safe_snapshot = {
        key: value for key, value in snapshot.items() if key in ALLOWED_SNAPSHOT_FEATURES
    }
    news_available = bool(historical_news_available)
    financial_available = bool(historical_financial_available)
    record = {
        "technical_score": _finite(safe_snapshot.get("technical_score")),
        "volume_score": _finite(safe_snapshot.get("volume_score")),
        "news_score": (
            _finite(safe_snapshot.get("news_score")) if news_available else np.nan
        ),
        "financial_score": (
            _finite(safe_snapshot.get("financial_score"))
            if financial_available
            else np.nan
        ),
        "risk_score": _finite(safe_snapshot.get("risk_score")),
        "final_score": _finite(final_score),
        "rsi": _finite(safe_snapshot.get("rsi")),
        "volatility_20d": _finite(safe_snapshot.get("volatility_20d")),
        "price_rows": _finite(safe_snapshot.get("price_rows")),
        "historical_news_available": float(news_available),
        "historical_financial_available": float(financial_available),
        "market_kr": float(market == "KR"),
        "market_us": float(market == "US"),
    }
    for key in OPTIONAL_FEATURES:
        record[key] = _finite(safe_snapshot.get(key))
    return record


def live_feature_record(
    *,
    technical_score: float,
    volume_score: float,
    news_score: float,
    financial_score: float,
    risk_score: float,
    final_score: float,
    latest: dict | None,
    price_rows: int,
    news_available: bool,
    financial_available: bool,
    market: str,
    point_in_time_features: dict[str, float] | None = None,
) -> dict[str, float]:
    latest = latest or {}
    close = _finite(latest.get("close"))
    ma5 = _finite(latest.get("ma5"))
    ma20 = _finite(latest.get("ma20"))
    record = {
        "technical_score": _finite(technical_score),
        "volume_score": _finite(volume_score),
        "news_score": _finite(news_score) if news_available else np.nan,
        "financial_score": _finite(financial_score) if financial_available else np.nan,
        "risk_score": _finite(risk_score),
        "final_score": _finite(final_score),
        "rsi": _finite(latest.get("rsi")),
        "volatility_20d": _finite(latest.get("volatility_20d")),
        "price_rows": float(price_rows),
        "historical_news_available": float(news_available),
        "historical_financial_available": float(financial_available),
        "market_kr": float(market == "KR"),
        "market_us": float(market == "US"),
        "recent_5d_return": _finite(latest.get("recent_5d_return")),
        "recent_20d_return": _finite(latest.get("recent_20d_return")),
        "ma5_gap": (
            (close / ma5 - 1) * 100
            if math.isfinite(close) and math.isfinite(ma5) and ma5
            else np.nan
        ),
        "ma20_gap": (
            (close / ma20 - 1) * 100
            if math.isfinite(close) and math.isfinite(ma20) and ma20
            else np.nan
        ),
        "macd": _finite(latest.get("macd")),
        "atr": _finite(latest.get("atr")),
        "volume_change_rate": _finite(latest.get("volume_change_rate")),
    }
    for key in POINT_IN_TIME_FEATURES:
        if point_in_time_features and key in point_in_time_features:
            record[key] = _finite(point_in_time_features.get(key))
        else:
            record.setdefault(key, np.nan)
    if point_in_time_features:
        record["market_regime"] = point_in_time_features.get(
            "market_regime",
            "sideways_low_vol",
        )
    return record


def build_ml_dataset(db: Session) -> tuple[pd.DataFrame, dict]:
    rows = db.execute(
        select(PredictionResult, Stock.market)
        .join(Stock, Stock.id == PredictionResult.stock_id)
        .where(
            PredictionResult.prediction_source == "historical_replay",
            PredictionResult.model_version == BASELINE_VERSION,
            PredictionResult.actual_return.is_not(None),
        )
        .order_by(PredictionResult.prediction_date.asc(), PredictionResult.stock_id.asc())
    ).all()
    records: list[dict] = []
    feature_map = {}
    if rows:
        dates = [prediction.prediction_date for prediction, _market in rows]
        feature_map = build_point_in_time_feature_map(
            db,
            start_date=min(dates),
            end_date=max(dates),
        )
    flat_excluded = 0
    invalid_excluded = 0
    for prediction, market in rows:
        snapshot = _json(prediction.feature_snapshot, {})
        if not isinstance(snapshot, dict):
            invalid_excluded += 1
            continue
        # Only the explicit historical snapshot whitelist is read. Target fields,
        # D+1 prices, and current data are never accepted as model inputs.
        actual_return = float(prediction.actual_return)
        if actual_return == 0:
            flat_excluded += 1
            continue
        features = _feature_record(
            snapshot=snapshot,
            final_score=prediction.final_score,
            market=market,
            historical_news_available=prediction.historical_news_available,
            historical_financial_available=prediction.historical_financial_available,
        )
        point_features = feature_map.get((prediction.stock_id, prediction.prediction_date), {})
        for key in POINT_IN_TIME_FEATURES:
            features[key] = _finite(point_features.get(key))
        records.append(
            {
                "prediction_id": prediction.id,
                "prediction_date": prediction.prediction_date,
                "stock_id": prediction.stock_id,
                "market": market,
                "market_regime": point_features.get(
                    "market_regime",
                    "sideways_low_vol",
                ),
                "direction_target": int(actual_return > 0),
                "return_target": actual_return,
                "baseline_probability": (
                    prediction.calibrated_up_probability
                    or prediction.up_probability
                )
                / 100,
                "baseline_return_midpoint": (
                    prediction.expected_range_low + prediction.expected_range_high
                )
                / 2,
                **features,
            }
        )
    frame = pd.DataFrame(records)
    metadata = {
        "source": "historical_replay",
        "total_historical_rows": len(rows),
        "usable_direction_rows": len(frame),
        "flat_excluded": flat_excluded,
        "invalid_feature_snapshot_excluded": invalid_excluded,
    }
    return frame, metadata


def select_feature_columns(frame: pd.DataFrame) -> list[str]:
    selected = [
        key for key in CORE_FEATURES if key not in {"news_score", "financial_score"}
    ]
    for key in ["news_score", "financial_score"]:
        if key in frame and frame[key].notna().mean() >= 0.2:
            selected.append(key)
    for key in OPTIONAL_FEATURES:
        if key in frame and frame[key].notna().mean() >= 0.5:
            selected.append(key)
    for key in POINT_FEATURES:
        if key in frame and frame[key].notna().mean() >= 0.5:
            selected.append(key)
    return selected


def chronological_split(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "train": frame.copy(),
            "calibration": frame.copy(),
            "test": frame.copy(),
            "dates": {},
        }
    ordered = frame.sort_values(["prediction_date", "stock_id"]).reset_index(drop=True)
    max_date = pd.Timestamp(ordered["prediction_date"].max())
    min_date = pd.Timestamp(ordered["prediction_date"].min())
    window_start = max(min_date, max_date - pd.DateOffset(months=24))
    ordered = ordered[pd.to_datetime(ordered["prediction_date"]) >= window_start].copy()
    train_end = window_start + pd.DateOffset(months=15)
    calibration_end = train_end + pd.DateOffset(months=3)
    test_end = calibration_end + pd.DateOffset(months=6)
    dates = pd.to_datetime(ordered["prediction_date"])
    train = ordered[dates < train_end].copy()
    calibration = ordered[(dates >= train_end) & (dates < calibration_end)].copy()
    test = ordered[(dates >= calibration_end) & (dates <= test_end)].copy()
    return {
        "train": train,
        "calibration": calibration,
        "test": test,
        "dates": {
            "train_start": train["prediction_date"].min() if not train.empty else None,
            "train_end": train["prediction_date"].max() if not train.empty else None,
            "calibration_start": (
                calibration["prediction_date"].min() if not calibration.empty else None
            ),
            "calibration_end": (
                calibration["prediction_date"].max() if not calibration.empty else None
            ),
            "test_start": test["prediction_date"].min() if not test.empty else None,
            "test_end": test["prediction_date"].max() if not test.empty else None,
        },
    }


def _classifier(model_type: str) -> Pipeline:
    if model_type == "logistic_regression":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1500,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        )
    if model_type == "hist_gradient_boosting_classifier":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=0.05,
                        max_iter=220,
                        max_leaf_nodes=15,
                        min_samples_leaf=30,
                        l2_regularization=0.2,
                        random_state=42,
                    ),
                ),
            ]
        )
    if model_type == "random_forest_classifier":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=320,
                        max_depth=10,
                        min_samples_leaf=20,
                        max_features="sqrt",
                        class_weight="balanced_subsample",
                        n_jobs=-1,
                        random_state=42,
                    ),
                ),
            ]
        )
    raise ValueError(f"지원하지 않는 분류 모델입니다: {model_type}")


def _regressor() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            (
                "model",
                HistGradientBoostingRegressor(
                    learning_rate=0.05,
                    max_iter=220,
                    max_leaf_nodes=15,
                    min_samples_leaf=30,
                    l2_regularization=0.2,
                    random_state=42,
                    loss="absolute_error",
                ),
            ),
        ]
    )


def _fit_probability_calibrator(
    raw_probabilities: np.ndarray,
    targets: np.ndarray,
) -> LogisticRegression | None:
    if len(np.unique(targets)) < 2:
        return None
    clipped = np.clip(raw_probabilities, 1e-5, 1 - 1e-5)
    logits = np.log(clipped / (1 - clipped)).reshape(-1, 1)
    calibrator = LogisticRegression(max_iter=500, random_state=42)
    calibrator.fit(logits, targets)
    return calibrator


def _apply_calibrator(
    calibrator: LogisticRegression | None,
    raw_probabilities: np.ndarray,
) -> np.ndarray:
    if calibrator is None:
        return np.clip(raw_probabilities, 1e-5, 1 - 1e-5)
    clipped = np.clip(raw_probabilities, 1e-5, 1 - 1e-5)
    logits = np.log(clipped / (1 - clipped)).reshape(-1, 1)
    return np.clip(calibrator.predict_proba(logits)[:, 1], 1e-5, 1 - 1e-5)


def expected_calibration_error(
    targets: np.ndarray,
    probabilities: np.ndarray,
    bins: int = 10,
) -> float:
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for index in range(bins):
        low, high = edges[index], edges[index + 1]
        mask = (
            (probabilities >= low) & (probabilities < high)
            if index < bins - 1
            else (probabilities >= low) & (probabilities <= high)
        )
        if not mask.any():
            continue
        ece += mask.mean() * abs(targets[mask].mean() - probabilities[mask].mean())
    return float(ece)


def _calibration_bins(
    targets: np.ndarray,
    probabilities: np.ndarray,
    bins: int = 10,
) -> list[dict]:
    result = []
    edges = np.linspace(0, 1, bins + 1)
    for index in range(bins):
        low, high = edges[index], edges[index + 1]
        mask = (
            (probabilities >= low) & (probabilities < high)
            if index < bins - 1
            else (probabilities >= low) & (probabilities <= high)
        )
        if not mask.any():
            continue
        result.append(
            {
                "low": round(low * 100, 1),
                "high": round(high * 100, 1),
                "count": int(mask.sum()),
                "predicted_mean": round(float(probabilities[mask].mean() * 100), 2),
                "observed_up_rate": round(float(targets[mask].mean() * 100), 2),
            }
        )
    return result


def classification_metrics(
    targets: np.ndarray,
    probabilities: np.ndarray,
) -> dict:
    predicted = (probabilities >= 0.5).astype(int)
    has_both_classes = len(np.unique(targets)) == 2
    return {
        "samples": int(len(targets)),
        "accuracy": round(float(accuracy_score(targets, predicted) * 100), 3),
        "precision_up": round(
            float(precision_score(targets, predicted, zero_division=0) * 100),
            3,
        ),
        "precision_down": round(
            float(
                precision_score(
                    targets,
                    predicted,
                    pos_label=0,
                    zero_division=0,
                )
                * 100
            ),
            3,
        ),
        "recall_up": round(
            float(recall_score(targets, predicted, zero_division=0) * 100),
            3,
        ),
        "recall_down": round(
            float(
                recall_score(
                    targets,
                    predicted,
                    pos_label=0,
                    zero_division=0,
                )
                * 100
            ),
            3,
        ),
        "f1": round(float(f1_score(targets, predicted, zero_division=0)), 5),
        "f1_macro": round(
            float(f1_score(targets, predicted, average="macro", zero_division=0)),
            5,
        ),
        "roc_auc": (
            round(float(roc_auc_score(targets, probabilities)), 5)
            if has_both_classes
            else None
        ),
        "pr_auc": (
            round(float(average_precision_score(targets, probabilities)), 5)
            if has_both_classes
            else None
        ),
        "brier_score": round(float(brier_score_loss(targets, probabilities)), 6),
        "log_loss": round(
            float(log_loss(targets, probabilities, labels=[0, 1])),
            6,
        ),
        "expected_calibration_error": round(
            expected_calibration_error(targets, probabilities),
            6,
        ),
        "mean_absolute_error": round(
            float(mean_absolute_error(targets, probabilities) * 100),
            3,
        ),
        "positive_rate": round(float(targets.mean() * 100), 3),
        "calibration_bins": _calibration_bins(targets, probabilities),
    }


def _monthly_walk_forward(
    frame: pd.DataFrame,
    feature_columns: list[str],
    model_type: str,
    evaluation_start: date,
) -> dict:
    ordered = frame.sort_values(["prediction_date", "stock_id"]).copy()
    ordered_dates = pd.to_datetime(ordered["prediction_date"])
    month_starts = sorted(
        {
            timestamp.to_period("M").to_timestamp()
            for timestamp in ordered_dates
            if timestamp.date() >= evaluation_start
        }
    )
    monthly: list[dict] = []
    for month_start in month_starts:
        month_end = month_start + pd.DateOffset(months=1)
        calibration_start = month_start - pd.DateOffset(months=3)
        train = ordered[ordered_dates < calibration_start]
        calibration = ordered[
            (ordered_dates >= calibration_start) & (ordered_dates < month_start)
        ]
        current = ordered[
            (ordered_dates >= month_start) & (ordered_dates < month_end)
        ]
        if (
            len(train) < MIN_TRAIN_SAMPLES
            or len(calibration) < MIN_CALIBRATION_SAMPLES
            or current.empty
        ):
            continue
        model = _classifier(model_type)
        model.fit(train[feature_columns], train["direction_target"])
        calibration_raw = model.predict_proba(calibration[feature_columns])[:, 1]
        calibrator = _fit_probability_calibrator(
            calibration_raw,
            calibration["direction_target"].to_numpy(),
        )
        current_raw = model.predict_proba(current[feature_columns])[:, 1]
        current_probability = _apply_calibrator(calibrator, current_raw)
        metrics = classification_metrics(
            current["direction_target"].to_numpy(),
            current_probability,
        )
        monthly.append({"month": month_start.strftime("%Y-%m"), **metrics})
    accuracies = [row["accuracy"] / 100 for row in monthly]
    return {
        "months": monthly,
        "month_count": len(monthly),
        "accuracy_std": (
            round(float(np.std(accuracies)), 5) if accuracies else None
        ),
        "worst_accuracy": (
            round(float(min(accuracies) * 100), 3) if accuracies else None
        ),
        "stable": bool(
            len(accuracies) >= 4
            and np.std(accuracies) <= 0.12
            and min(accuracies) >= 0.40
        ),
    }


def _extended_test_metrics(
    *,
    calibration_targets: np.ndarray,
    calibration_probabilities: np.ndarray,
    calibration_returns: np.ndarray,
    test_targets: np.ndarray,
    test_probabilities: np.ndarray,
    test_returns: np.ndarray,
) -> dict:
    threshold_selection = select_confidence_threshold(
        calibration_targets,
        calibration_probabilities,
        calibration_returns,
    )
    threshold = threshold_selection["selected_threshold"]
    return classification_metrics(test_targets, test_probabilities) | {
        "meaningful_move": meaningful_move_metrics(
            test_returns,
            test_probabilities,
        ),
        "high_confidence": selective_signal_metrics(
            test_targets,
            test_probabilities,
            test_returns,
            threshold=threshold,
        ),
        "confidence_threshold": threshold,
        "threshold_selection": threshold_selection,
    }


def _candidate_eligibility(
    *,
    candidate: dict,
    baseline: dict,
    walk_forward: dict,
) -> tuple[bool, list[str], str | None]:
    improvements = {
        "accuracy": candidate["accuracy"] >= baseline["accuracy"] + 0.20,
        "brier": candidate["brier_score"] < baseline["brier_score"],
        "calibration": (
            candidate["expected_calibration_error"]
            <= baseline["expected_calibration_error"] + 0.002
        ),
        "high_confidence_return": (
            candidate["high_confidence"]["trades"] >= 150
            and (
                candidate["high_confidence"]["average_net_return"] or -999
            )
            > (
                baseline["high_confidence"]["average_net_return"] or -999
            )
        ),
    }
    broad_eligible = bool(
        improvements["brier"]
        and improvements["calibration"]
        and improvements["accuracy"]
        and improvements["high_confidence_return"]
        and walk_forward.get("stable", False)
    )
    high_confidence = candidate["high_confidence"]
    selective_eligible = bool(
        candidate["brier_score"] <= baseline["brier_score"]
        and candidate["expected_calibration_error"]
        <= baseline["expected_calibration_error"] + 0.005
        and high_confidence["trades"] >= 500
        and (high_confidence["accuracy"] or 0) >= 55
        and (high_confidence["average_net_return"] or -999) > 0
        and 2 <= (high_confidence["signal_frequency"] or 0) <= 35
        and walk_forward.get("stable", False)
    )
    eligible = broad_eligible or selective_eligible
    mode = (
        "broad_direction"
        if broad_eligible
        else "selective_high_confidence"
        if selective_eligible
        else None
    )
    reasons = [
        f"{name}: {'통과' if passed else '미달'}"
        for name, passed in improvements.items()
    ]
    reasons.append(
        f"워크포워드 안정성: {'통과' if walk_forward.get('stable') else '미달'}"
    )
    reasons.append(
        "선택 신호 기준: "
        + ("통과" if selective_eligible else "미달")
        + " (적중률 55%+, 500건+, 비용 차감 수익 양수)"
    )
    return eligible, reasons, mode


def _monthly_walk_forward_ensemble(
    frame: pd.DataFrame,
    feature_columns: list[str],
    model_types: list[str],
    evaluation_start: date,
) -> dict:
    ordered = frame.sort_values(["prediction_date", "stock_id"]).copy()
    ordered_dates = pd.to_datetime(ordered["prediction_date"])
    month_starts = sorted(
        {
            timestamp.to_period("M").to_timestamp()
            for timestamp in ordered_dates
            if timestamp.date() >= evaluation_start
        }
    )
    monthly = []
    for month_start in month_starts:
        calibration_start = month_start - pd.DateOffset(months=3)
        month_end = month_start + pd.DateOffset(months=1)
        train = ordered[ordered_dates < calibration_start]
        calibration = ordered[
            (ordered_dates >= calibration_start) & (ordered_dates < month_start)
        ]
        current = ordered[
            (ordered_dates >= month_start) & (ordered_dates < month_end)
        ]
        if (
            len(train) < MIN_TRAIN_SAMPLES
            or len(calibration) < MIN_CALIBRATION_SAMPLES
            or current.empty
        ):
            continue
        calibration_components = {}
        current_components = {}
        for model_type in model_types:
            model = _classifier(model_type)
            model.fit(train[feature_columns], train["direction_target"])
            calibration_raw = model.predict_proba(calibration[feature_columns])[:, 1]
            calibrator = _fit_probability_calibrator(
                calibration_raw,
                calibration["direction_target"].to_numpy(),
            )
            calibration_components[model_type] = _apply_calibrator(
                calibrator,
                calibration_raw,
            )
            current_components[model_type] = _apply_calibrator(
                calibrator,
                model.predict_proba(current[feature_columns])[:, 1],
            )
        calibration_regimes = calibration.get(
            "market_regime",
            pd.Series("unknown", index=calibration.index),
        ).to_numpy()
        current_regimes = current.get(
            "market_regime",
            pd.Series("unknown", index=current.index),
        ).to_numpy()
        weights = fit_regime_weights(
            calibration["direction_target"].to_numpy(),
            calibration_components,
            calibration_regimes,
        )
        combined_raw = combine_probabilities(
            current_components,
            current_regimes,
            weights,
        )
        calibration_combined = combine_probabilities(
            calibration_components,
            calibration_regimes,
            weights,
        )
        ensemble_calibrator = _fit_probability_calibrator(
            calibration_combined,
            calibration["direction_target"].to_numpy(),
        )
        probability = _apply_calibrator(ensemble_calibrator, combined_raw)
        monthly.append(
            {
                "month": month_start.strftime("%Y-%m"),
                **classification_metrics(
                    current["direction_target"].to_numpy(),
                    probability,
                ),
            }
        )
    accuracies = [row["accuracy"] / 100 for row in monthly]
    return {
        "months": monthly,
        "month_count": len(monthly),
        "accuracy_std": round(float(np.std(accuracies)), 5) if accuracies else None,
        "worst_accuracy": (
            round(float(min(accuracies) * 100), 3) if accuracies else None
        ),
        "stable": bool(
            len(accuracies) >= 4
            and np.std(accuracies) <= 0.12
            and min(accuracies) >= 0.40
        ),
        "method": "expanding_walk_forward_with_3m_calibration",
    }


def _serialize_model(version: ModelVersion, *, recommended: bool = False) -> dict:
    return {
        "id": version.id,
        "version_name": version.version_name,
        "model_type": version.model_type,
        "status": version.status,
        "is_active": version.is_active,
        "feature_schema": _json(version.feature_schema_json, []),
        "training_summary": _json(version.training_summary_json, {}),
        "validation_summary": _json(version.validation_summary_json, {}),
        "test_summary": _json(version.test_summary_json, {}),
        "artifact_path": version.artifact_path,
        "metadata_path": version.metadata_path,
        "created_at": version.created_at,
        "can_activate": (
            version.status in {"candidate", "active"}
            and version.model_type
            in {
                "logistic_regression",
                "hist_gradient_boosting_classifier",
                "random_forest_classifier",
                "dynamic_regime_ensemble",
            }
        ),
        "recommended": recommended,
    }


def active_model_version(db: Session) -> ModelVersion:
    active = db.scalar(
        select(ModelVersion)
        .where(ModelVersion.is_active.is_(True))
        .order_by(ModelVersion.created_at.desc())
    )
    if active:
        return active
    baseline = db.scalar(
        select(ModelVersion).where(ModelVersion.version_name == BASELINE_VERSION)
    )
    if baseline is None:
        baseline = ModelVersion(
            version_name=BASELINE_VERSION,
            model_type="baseline",
            status="active",
            is_active=True,
        )
        db.add(baseline)
        db.flush()
    else:
        baseline.is_active = True
        baseline.status = "active"
    return baseline


def model_overview(db: Session) -> dict:
    active = active_model_version(db)
    db.commit()
    versions = list(
        db.scalars(
            select(ModelVersion)
            .order_by(ModelVersion.created_at.desc(), ModelVersion.id.desc())
            .limit(20)
        ).all()
    )
    eligible = [
        version
        for version in versions
        if version.status in {"candidate", "active"}
        and version.model_type
        in {
            "logistic_regression",
            "hist_gradient_boosting_classifier",
            "random_forest_classifier",
            "dynamic_regime_ensemble",
        }
    ]
    recommended_id = (
        min(
            eligible,
            key=lambda version: _json(
                version.test_summary_json,
                {"brier_score": 999},
            ).get("brier_score", 999),
        ).id
        if eligible
        else None
    )
    experiments = list(
        db.scalars(
            select(ModelExperiment)
            .order_by(ModelExperiment.created_at.desc(), ModelExperiment.id.desc())
            .limit(20)
        ).all()
    )
    activation_history = list(
        db.scalars(
            select(ModelActivationEvent)
            .order_by(ModelActivationEvent.created_at.desc())
            .limit(30)
        ).all()
    )
    return {
        "active_model": _serialize_model(
            active,
            recommended=active.id == recommended_id,
        ),
        "baseline_version": BASELINE_VERSION,
        "models": [
            _serialize_model(
                version,
                recommended=version.id == recommended_id,
            )
            for version in versions
        ],
        "experiments": [
            {
                "id": row.id,
                "experiment_name": row.experiment_name,
                "model_type": row.model_type,
                "feature_set_version": row.feature_set_version,
                "train_start_date": row.train_start_date,
                "train_end_date": row.train_end_date,
                "calibration_start_date": row.calibration_start_date,
                "calibration_end_date": row.calibration_end_date,
                "test_start_date": row.test_start_date,
                "test_end_date": row.test_end_date,
                "parameters": _json(row.parameters_json, {}),
                "metrics": _json(row.metrics_json, {}),
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in experiments
        ],
        "activation_history": [
            {
                "id": row.id,
                "from_version": row.from_version,
                "to_version": row.to_version,
                "action": row.action,
                "reason": row.reason,
                "created_at": row.created_at,
            }
            for row in activation_history
        ],
    }


def model_detail(db: Session, model_id: int) -> dict | None:
    version = db.get(ModelVersion, model_id)
    return _serialize_model(version) if version else None


def _write_artifacts(
    *,
    version_name: str,
    bundle: dict,
    metadata: dict,
) -> tuple[str, str]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    artifact = MODEL_DIR / f"{version_name}.joblib"
    metadata_path = MODEL_DIR / f"{version_name}.json"
    joblib.dump(bundle, artifact)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return str(artifact), str(metadata_path)


def _save_experiment_and_version(
    db: Session,
    *,
    experiment_name: str,
    version_name: str,
    model_type: str,
    split: dict,
    parameters: dict,
    metrics: dict,
    status: str,
    artifact_path: str,
    metadata_path: str,
    feature_columns: list[str],
) -> ModelVersion:
    dates = split["dates"]
    db.add(
        ModelExperiment(
            experiment_name=experiment_name,
            model_type=model_type,
            feature_set_version=FEATURE_SET_VERSION,
            train_start_date=dates.get("train_start"),
            train_end_date=dates.get("train_end"),
            calibration_start_date=dates.get("calibration_start"),
            calibration_end_date=dates.get("calibration_end"),
            test_start_date=dates.get("test_start"),
            test_end_date=dates.get("test_end"),
            parameters_json=json.dumps(parameters, ensure_ascii=False),
            metrics_json=json.dumps(metrics, ensure_ascii=False),
            status=status,
        )
    )
    version = ModelVersion(
        version_name=version_name,
        model_type=model_type,
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        feature_schema_json=json.dumps(feature_columns, ensure_ascii=False),
        training_summary_json=json.dumps(metrics.get("training", {}), ensure_ascii=False),
        validation_summary_json=json.dumps(
            metrics.get("calibration", {}),
            ensure_ascii=False,
        ),
        test_summary_json=json.dumps(
            metrics.get("test", {})
            | {
                "baseline": metrics.get("baseline_test"),
                "walk_forward": metrics.get("walk_forward"),
                "candidate_criteria": metrics.get("candidate_criteria"),
                "regime_weights": metrics.get("regime_weights"),
            },
            ensure_ascii=False,
        ),
        status=status,
        is_active=False,
    )
    db.add(version)
    db.flush()
    return version


def train_ml_candidates(db: Session) -> dict:
    frame, dataset_metadata = build_ml_dataset(db)
    split = chronological_split(frame)
    train = split["train"]
    calibration = split["calibration"]
    test = split["test"]
    counts = {
        "training": len(train),
        "calibration": len(calibration),
        "test": len(test),
    }
    if (
        counts["training"] < MIN_TRAIN_SAMPLES
        or counts["calibration"] < MIN_CALIBRATION_SAMPLES
        or counts["test"] < MIN_TEST_SAMPLES
    ):
        experiment = ModelExperiment(
            experiment_name=f"ml-candidate-insufficient-{_utcnow():%Y%m%d-%H%M%S}",
            model_type="candidate_suite",
            feature_set_version=FEATURE_SET_VERSION,
            train_start_date=split["dates"].get("train_start"),
            train_end_date=split["dates"].get("train_end"),
            calibration_start_date=split["dates"].get("calibration_start"),
            calibration_end_date=split["dates"].get("calibration_end"),
            test_start_date=split["dates"].get("test_start"),
            test_end_date=split["dates"].get("test_end"),
            parameters_json="{}",
            metrics_json=json.dumps(
                {"counts": counts, "dataset": dataset_metadata},
                ensure_ascii=False,
            ),
            status="rejected",
        )
        db.add(experiment)
        db.commit()
        return {
            "status": "insufficient",
            "message": "ML 후보 생성 보류: 과적합 위험 또는 검증 표본 부족",
            "counts": counts,
            "minimums": {
                "training": MIN_TRAIN_SAMPLES,
                "calibration": MIN_CALIBRATION_SAMPLES,
                "test": MIN_TEST_SAMPLES,
            },
            "overview": model_overview(db),
        }

    feature_columns = select_feature_columns(frame)
    baseline_test = _extended_test_metrics(
        calibration_targets=calibration["direction_target"].to_numpy(),
        calibration_probabilities=calibration["baseline_probability"].to_numpy(),
        calibration_returns=calibration["return_target"].to_numpy(),
        test_targets=test["direction_target"].to_numpy(),
        test_probabilities=test["baseline_probability"].to_numpy(),
        test_returns=test["return_target"].to_numpy(),
    )
    timestamp = _utcnow().strftime("%Y%m%d-%H%M%S-%f")
    experiment_name = f"ml-direction-candidates-{timestamp}"
    trained: list[dict] = []
    candidate_versions: list[ModelVersion] = []
    component_outputs: dict[str, dict] = {}
    classifier_types = [
        "logistic_regression",
        "hist_gradient_boosting_classifier",
        "random_forest_classifier",
    ]

    for model_type in classifier_types:
        model = _classifier(model_type)
        model.fit(train[feature_columns], train["direction_target"])
        train_probability = model.predict_proba(train[feature_columns])[:, 1]
        calibration_raw = model.predict_proba(calibration[feature_columns])[:, 1]
        calibrator = _fit_probability_calibrator(
            calibration_raw,
            calibration["direction_target"].to_numpy(),
        )
        calibration_probability = _apply_calibrator(calibrator, calibration_raw)
        test_raw = model.predict_proba(test[feature_columns])[:, 1]
        test_probability = _apply_calibrator(calibrator, test_raw)
        walk_forward = _monthly_walk_forward(
            frame,
            feature_columns,
            model_type,
            split["dates"]["calibration_start"],
        )
        test_metrics = _extended_test_metrics(
            calibration_targets=calibration["direction_target"].to_numpy(),
            calibration_probabilities=calibration_probability,
            calibration_returns=calibration["return_target"].to_numpy(),
            test_targets=test["direction_target"].to_numpy(),
            test_probabilities=test_probability,
            test_returns=test["return_target"].to_numpy(),
        )
        metrics = {
            "dataset": dataset_metadata,
            "training": classification_metrics(
                train["direction_target"].to_numpy(),
                train_probability,
            ),
            "calibration": classification_metrics(
                calibration["direction_target"].to_numpy(),
                calibration_probability,
            ),
            "test": test_metrics,
            "baseline_test": baseline_test,
            "walk_forward": walk_forward,
            "split_counts": counts,
        }
        eligible, eligibility_reasons, eligibility_mode = _candidate_eligibility(
            candidate=test_metrics,
            baseline=baseline_test,
            walk_forward=walk_forward,
        )
        metrics["candidate_criteria"] = {
            "eligible": eligible,
            "mode": eligibility_mode,
            "reasons": eligibility_reasons,
            "automatic_activation": False,
        }
        status = "candidate" if eligible else "rejected"
        version_name = f"{model_type}-v2-{timestamp}"
        metadata = {
            "version_name": version_name,
            "model_type": model_type,
            "feature_set_version": FEATURE_SET_VERSION,
            "feature_columns": feature_columns,
            "split_dates": split["dates"],
            "metrics": metrics,
            "status": status,
            "is_active": False,
            "created_at": _utcnow().isoformat(),
            "flat_excluded": dataset_metadata["flat_excluded"],
        }
        artifact_path, metadata_path = _write_artifacts(
            version_name=version_name,
            bundle={
                "model": model,
                "calibrator": calibrator,
                "feature_columns": feature_columns,
                "model_type": model_type,
                "version_name": version_name,
                "confidence_threshold": test_metrics["confidence_threshold"],
            },
            metadata=metadata,
        )
        version = _save_experiment_and_version(
            db,
            experiment_name=experiment_name,
            version_name=version_name,
            model_type=model_type,
            split=split,
            parameters=_model_parameters(model),
            metrics=metrics,
            status=status,
            artifact_path=artifact_path,
            metadata_path=metadata_path,
            feature_columns=feature_columns,
        )
        if eligible:
            candidate_versions.append(version)
        trained.append(
            {
                "version_name": version_name,
                "model_type": model_type,
                "status": status,
                "metrics": metrics,
            }
        )
        component_outputs[model_type] = {
            "model": model,
            "calibrator": calibrator,
            "calibration_probability": calibration_probability,
            "test_probability": test_probability,
            "train_probability": train_probability,
        }

    calibration_regimes = calibration.get(
        "market_regime",
        pd.Series("unknown", index=calibration.index),
    ).to_numpy()
    test_regimes = test.get(
        "market_regime",
        pd.Series("unknown", index=test.index),
    ).to_numpy()
    train_regimes = train.get(
        "market_regime",
        pd.Series("unknown", index=train.index),
    ).to_numpy()
    regime_weights = fit_regime_weights(
        calibration["direction_target"].to_numpy(),
        {
            name: output["calibration_probability"]
            for name, output in component_outputs.items()
        },
        calibration_regimes,
    )
    ensemble_calibration_raw = combine_probabilities(
        {
            name: output["calibration_probability"]
            for name, output in component_outputs.items()
        },
        calibration_regimes,
        regime_weights,
    )
    ensemble_test_raw = combine_probabilities(
        {
            name: output["test_probability"]
            for name, output in component_outputs.items()
        },
        test_regimes,
        regime_weights,
    )
    ensemble_train_raw = combine_probabilities(
        {
            name: output["train_probability"]
            for name, output in component_outputs.items()
        },
        train_regimes,
        regime_weights,
    )
    ensemble_calibrator = _fit_probability_calibrator(
        ensemble_calibration_raw,
        calibration["direction_target"].to_numpy(),
    )
    ensemble_calibration = _apply_calibrator(
        ensemble_calibrator,
        ensemble_calibration_raw,
    )
    ensemble_test = _apply_calibrator(
        ensemble_calibrator,
        ensemble_test_raw,
    )
    ensemble_train = _apply_calibrator(
        ensemble_calibrator,
        ensemble_train_raw,
    )
    ensemble_walk_forward = _monthly_walk_forward_ensemble(
        frame,
        feature_columns,
        classifier_types,
        split["dates"]["calibration_start"],
    )
    ensemble_test_metrics = _extended_test_metrics(
        calibration_targets=calibration["direction_target"].to_numpy(),
        calibration_probabilities=ensemble_calibration,
        calibration_returns=calibration["return_target"].to_numpy(),
        test_targets=test["direction_target"].to_numpy(),
        test_probabilities=ensemble_test,
        test_returns=test["return_target"].to_numpy(),
    )
    (
        ensemble_eligible,
        ensemble_reasons,
        ensemble_eligibility_mode,
    ) = _candidate_eligibility(
        candidate=ensemble_test_metrics,
        baseline=baseline_test,
        walk_forward=ensemble_walk_forward,
    )
    ensemble_status = "candidate" if ensemble_eligible else "rejected"
    ensemble_version_name = f"dynamic_regime_ensemble-v2-{timestamp}"
    ensemble_metrics = {
        "dataset": dataset_metadata,
        "training": classification_metrics(
            train["direction_target"].to_numpy(),
            ensemble_train,
        ),
        "calibration": classification_metrics(
            calibration["direction_target"].to_numpy(),
            ensemble_calibration,
        ),
        "test": ensemble_test_metrics,
        "baseline_test": baseline_test,
        "walk_forward": ensemble_walk_forward,
        "regime_weights": regime_weights,
        "candidate_criteria": {
            "eligible": ensemble_eligible,
            "mode": ensemble_eligibility_mode,
            "reasons": ensemble_reasons,
            "automatic_activation": False,
        },
        "split_counts": counts,
    }
    ensemble_bundle = {
        "components": {
            name: {
                "model": output["model"],
                "calibrator": output["calibrator"],
            }
            for name, output in component_outputs.items()
        },
        "regime_weights": regime_weights,
        "ensemble_calibrator": ensemble_calibrator,
        "feature_columns": feature_columns,
        "model_type": "dynamic_regime_ensemble",
        "version_name": ensemble_version_name,
        "confidence_threshold": ensemble_test_metrics["confidence_threshold"],
    }
    artifact_path, metadata_path = _write_artifacts(
        version_name=ensemble_version_name,
        bundle=ensemble_bundle,
        metadata={
            "version_name": ensemble_version_name,
            "model_type": "dynamic_regime_ensemble",
            "feature_columns": feature_columns,
            "regime_weights": regime_weights,
            "metrics": ensemble_metrics,
            "status": ensemble_status,
            "is_active": False,
        },
    )
    ensemble_version = _save_experiment_and_version(
        db,
        experiment_name=experiment_name,
        version_name=ensemble_version_name,
        model_type="dynamic_regime_ensemble",
        split=split,
        parameters={"components": classifier_types, "weighting": "inverse_brier_by_regime"},
        metrics=ensemble_metrics,
        status=ensemble_status,
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        feature_columns=feature_columns,
    )
    if ensemble_eligible:
        candidate_versions.append(ensemble_version)
    trained.append(
        {
            "version_name": ensemble_version_name,
            "model_type": "dynamic_regime_ensemble",
            "status": ensemble_status,
            "metrics": ensemble_metrics,
        }
    )

    return_model = _regressor()
    return_model.fit(train[feature_columns], train["return_target"])
    return_prediction = return_model.predict(test[feature_columns])
    return_mae = float(mean_absolute_error(test["return_target"], return_prediction))
    baseline_return_mae = float(
        mean_absolute_error(
            test["return_target"],
            test["baseline_return_midpoint"],
        )
    )
    return_status = "candidate" if return_mae < baseline_return_mae else "rejected"
    return_version_name = f"hist_gradient_boosting_regressor-v2-{timestamp}"
    return_metrics = {
        "dataset": dataset_metadata,
        "training": {"samples": len(train)},
        "calibration": {"samples": len(calibration)},
        "test": {
            "samples": len(test),
            "mean_absolute_error": round(return_mae, 6),
            "baseline_mean_absolute_error": round(baseline_return_mae, 6),
        },
        "candidate_criteria": {
            "eligible": return_status == "candidate",
            "reasons": ["MAE가 기준 모델보다 낮아야 함"],
            "automatic_activation": False,
        },
        "split_counts": counts,
    }
    artifact_path, metadata_path = _write_artifacts(
        version_name=return_version_name,
        bundle={
            "model": return_model,
            "feature_columns": feature_columns,
            "model_type": "hist_gradient_boosting_regressor",
            "version_name": return_version_name,
        },
        metadata={
            "version_name": return_version_name,
            "model_type": "hist_gradient_boosting_regressor",
            "feature_columns": feature_columns,
            "metrics": return_metrics,
            "status": return_status,
            "is_active": False,
        },
    )
    _save_experiment_and_version(
        db,
        experiment_name=experiment_name,
        version_name=return_version_name,
        model_type="hist_gradient_boosting_regressor",
        split=split,
        parameters=_model_parameters(return_model),
        metrics=return_metrics,
        status=return_status,
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        feature_columns=feature_columns,
    )
    trained.append(
        {
            "version_name": return_version_name,
            "model_type": "hist_gradient_boosting_regressor",
            "status": return_status,
            "metrics": return_metrics,
        }
    )

    if candidate_versions:
        recommended = min(
            candidate_versions,
            key=lambda version: _json(
                version.test_summary_json,
                {"brier_score": 999},
            ).get("brier_score", 999),
        )
        recommended_name = recommended.version_name
    else:
        recommended_name = None
    db.commit()
    return {
        "status": "completed",
        "message": (
            "검증 기준을 통과한 ML 후보를 생성했습니다."
            if recommended_name
            else "학습은 완료됐지만 최종 검증 기준을 모두 통과한 후보는 없습니다."
        ),
        "recommended_version": recommended_name,
        "baseline_test": baseline_test,
        "trained_models": trained,
        "counts": counts,
        "feature_columns": feature_columns,
        "overview": model_overview(db),
    }


def activate_model(db: Session, model_id: int) -> dict:
    selected = db.get(ModelVersion, model_id)
    if not selected:
        raise ValueError("모델 버전을 찾을 수 없습니다.")
    if selected.model_type not in {
        "logistic_regression",
        "hist_gradient_boosting_classifier",
        "random_forest_classifier",
        "dynamic_regime_ensemble",
    }:
        raise ValueError("방향성 분류 모델만 운영 예측 모델로 적용할 수 있습니다.")
    if selected.status not in {"candidate", "active"}:
        raise ValueError("최종 검증 기준을 통과한 후보만 적용할 수 있습니다.")
    previous = db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)))
    for version in db.scalars(select(ModelVersion).where(ModelVersion.is_active.is_(True))):
        version.is_active = False
        version.status = "baseline" if version.model_type == "baseline" else "candidate"
    selected.is_active = True
    selected.status = "active"
    db.add(
        ModelActivationEvent(
            from_version=previous.version_name if previous else None,
            to_version=selected.version_name,
            action="activate",
            reason="user_confirmed_candidate_activation",
        )
    )
    db.commit()
    return model_overview(db)


def restore_baseline_model(db: Session) -> dict:
    previous = db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)))
    baseline = db.scalar(
        select(ModelVersion).where(ModelVersion.version_name == BASELINE_VERSION)
    )
    if baseline is None:
        baseline = ModelVersion(
            version_name=BASELINE_VERSION,
            model_type="baseline",
        )
        db.add(baseline)
        db.flush()
    for version in db.scalars(select(ModelVersion).where(ModelVersion.is_active.is_(True))):
        version.is_active = False
        version.status = "candidate" if version.model_type != "baseline" else "baseline"
    baseline.is_active = True
    baseline.status = "active"
    db.add(
        ModelActivationEvent(
            from_version=previous.version_name if previous else None,
            to_version=baseline.version_name,
            action="restore_baseline",
            reason="user_requested_restore",
        )
    )
    db.commit()
    return model_overview(db)


@lru_cache(maxsize=8)
def _load_artifact(path: str, modified_ns: int) -> dict:
    del modified_ns
    return joblib.load(path)


def predict_with_active_model(
    db: Session,
    *,
    live_features: dict[str, float],
    baseline_prediction: dict,
) -> dict:
    active = active_model_version(db)
    if active.model_type == "baseline" or not active.artifact_path:
        return {
            **baseline_prediction,
            "raw_up_probability": baseline_prediction["up_probability"],
            "model_calibrated_probability": None,
            "active_model": active,
        }
    artifact_path = Path(active.artifact_path)
    if not artifact_path.exists():
        raise FileNotFoundError("활성 ML 모델 파일을 찾을 수 없습니다.")
    bundle = _load_artifact(
        str(artifact_path),
        artifact_path.stat().st_mtime_ns,
    )
    feature_columns = bundle["feature_columns"]
    frame = pd.DataFrame(
        [{key: live_features.get(key, np.nan) for key in feature_columns}]
    )
    if bundle.get("model_type") == "dynamic_regime_ensemble":
        component_probabilities = {}
        for name, component in bundle["components"].items():
            component_raw = float(
                component["model"].predict_proba(frame)[:, 1][0]
            )
            component_probabilities[name] = float(
                _apply_calibrator(
                    component.get("calibrator"),
                    np.array([component_raw]),
                )[0]
            )
        raw_probability = combine_one(
            component_probabilities,
            str(live_features.get("market_regime", "unknown")),
            bundle["regime_weights"],
        )
        calibrated_probability = float(
            _apply_calibrator(
                bundle.get("ensemble_calibrator"),
                np.array([raw_probability]),
            )[0]
        )
    else:
        raw_probability = float(bundle["model"].predict_proba(frame)[:, 1][0])
        calibrated_probability = float(
            _apply_calibrator(
                bundle.get("calibrator"),
                np.array([raw_probability]),
            )[0]
        )
    return {
        **baseline_prediction,
        "up_probability": round(calibrated_probability * 100, 1),
        "down_probability": round((1 - calibrated_probability) * 100, 1),
        "raw_up_probability": round(raw_probability * 100, 1),
        "model_calibrated_probability": round(calibrated_probability * 100, 1),
        "model_version": active.version_name,
        "active_model": active,
    }


def selective_signal_decision(
    version: ModelVersion,
    *,
    probability: float,
    data_quality: float,
    liquidity_percentile: float | None,
    volatility: float | None,
) -> dict:
    summary = _json(version.test_summary_json, {})
    threshold = float(summary.get("confidence_threshold") or 0.65)
    confidence = max(probability / 100, 1 - probability / 100)
    reasons = []
    if confidence < threshold:
        reasons.append(
            f"방향 확률이 고신뢰 기준 {threshold * 100:.0f}%에 미달합니다."
        )
    if data_quality < 70:
        reasons.append("데이터 품질 점수가 70점 미만입니다.")
    if liquidity_percentile is not None and liquidity_percentile < 0.20:
        reasons.append("시장 내 거래대금 하위 20%로 체결 위험이 큽니다.")
    if volatility is not None and volatility >= 80:
        reasons.append("연환산 변동성이 80% 이상입니다.")
    return {
        "status": "defer" if reasons else "high_confidence_signal",
        "threshold": round(threshold * 100, 1),
        "confidence": round(confidence * 100, 1),
        "reasons": reasons,
    }


def probability_context(version: ModelVersion, probability: float) -> dict:
    summary = _json(version.test_summary_json, {})
    for bucket in summary.get("calibration_bins", []):
        if bucket["low"] <= probability <= bucket["high"]:
            return {
                "sample_count": bucket["count"],
                "observed_up_rate": bucket["observed_up_rate"],
            }
    return {
        "sample_count": int(summary.get("samples", 0)),
        "observed_up_rate": summary.get("positive_rate"),
    }


def confidence_from_active_model(
    version: ModelVersion,
    *,
    probability: float,
    base_confidence: str,
    data_quality: float,
    volatility: float | None,
    news_available: bool,
    financial_available: bool,
) -> dict:
    test = _json(version.test_summary_json, {})
    context = probability_context(version, probability)
    score = 0
    reasons = [
        f"활성 ML 모델: {version.version_name}",
        f"최종 테스트 표본: {int(test.get('samples', 0))}건",
    ]
    accuracy = test.get("accuracy")
    brier = test.get("brier_score")
    ece = test.get("expected_calibration_error")
    if accuracy is not None:
        score += 1 if accuracy >= 55 else -1 if accuracy < 50 else 0
        reasons.append(f"최종 테스트 방향 적중률 {accuracy:.1f}%")
    if brier is not None:
        score += 1 if brier <= 0.24 else -1
        reasons.append(f"Brier Score {brier:.4f}")
    if ece is not None:
        score += 1 if ece <= 0.08 else -1
        reasons.append(f"ECE {ece:.4f}")
    score += 1 if data_quality >= 90 else -2 if data_quality < 60 else -1 if data_quality < 75 else 0
    if volatility is not None and volatility > 70:
        score -= 2
        reasons.append(f"현재 연환산 변동성 {volatility:.1f}%")
    elif volatility is not None and volatility > 45:
        score -= 1
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
    if base_confidence == "low" and level in {"high", "medium"}:
        level = "low"
    return {
        "level": level,
        "score": score,
        "sample_count": int(test.get("samples", 0)),
        "calibration": {
            "sample_count": context["sample_count"],
            "observed_up_rate": context["observed_up_rate"],
            "calibrated_probability": probability,
        },
        "accuracy": accuracy,
        "recent_3m_accuracy": None,
        "mean_absolute_error": test.get("mean_absolute_error"),
        "range_accuracy": None,
        "reasons": reasons,
    }
