import json
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import ModelVersion, PredictionResult, Stock
from app.services import ml_model_service
from app.services.ml_model_service import (
    CORE_FEATURES,
    activate_model,
    active_model_version,
    build_ml_dataset,
    chronological_split,
    predict_with_active_model,
    restore_baseline_model,
    train_ml_candidates,
)
from app.services.prediction_engine import RuleBasedPredictionModel


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def add_stock(db: Session, ticker: str = "MLTEST") -> Stock:
    stock = Stock(
        ticker=ticker,
        name=ticker,
        market="US",
        country="US",
        currency="USD",
        is_listed=True,
    )
    db.add(stock)
    db.flush()
    return stock


def add_prediction(
    db: Session,
    stock: Stock,
    *,
    source: str,
    prediction_date: date,
    future_marker: float = 999,
) -> PredictionResult:
    row = PredictionResult(
        stock_id=stock.id,
        prediction_date=prediction_date,
        target_date=prediction_date + timedelta(days=1),
        final_score=65,
        up_probability=70,
        down_probability=30,
        expected_range_low=-2,
        expected_range_high=3,
        confidence_level="low",
        model_version=RuleBasedPredictionModel.version,
        horizon_days=1,
        prediction_source=source,
        raw_up_probability=70,
        calibrated_up_probability=65,
        actual_return=1.5,
        actual_direction="up",
        is_correct=True,
        range_hit=True,
        absolute_error=1,
        historical_news_available=False,
        historical_financial_available=False,
        feature_snapshot=json.dumps(
            {
                "technical_score": 30,
                "volume_score": 20,
                "news_score": 0,
                "financial_score": 0,
                "risk_score": 15,
                "rsi": 58,
                "volatility_20d": 28,
                "price_rows": 300,
                "future_close": future_marker,
                "actual_return": 99,
            }
        ),
    )
    db.add(row)
    db.flush()
    return row


def synthetic_dataset() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    start = date(2024, 6, 22)
    records = []
    prediction_id = 1
    for day in range(731):
        prediction_date = start + timedelta(days=day)
        for stock_id in range(4):
            signal = 1 if (day + stock_id) % 2 == 0 else 0
            technical = (45 if signal else -45) + rng.normal(0, 5)
            records.append(
                {
                    "prediction_id": prediction_id,
                    "prediction_date": prediction_date,
                    "stock_id": stock_id + 1,
                    "market": "US",
                    "direction_target": signal,
                    "return_target": 1.5 if signal else -1.5,
                    "baseline_probability": 0.1 if signal else 0.9,
                    "baseline_return_midpoint": 0.0,
                    "technical_score": technical,
                    "volume_score": technical * 0.4,
                    "news_score": np.nan,
                    "financial_score": np.nan,
                    "risk_score": 20,
                    "final_score": 65 if signal else 35,
                    "rsi": 60 if signal else 40,
                    "volatility_20d": 30,
                    "price_rows": 300,
                    "historical_news_available": 0,
                    "historical_financial_available": 0,
                    "market_kr": 0,
                    "market_us": 1,
                    "recent_5d_return": np.nan,
                    "recent_20d_return": np.nan,
                    "ma5_gap": np.nan,
                    "ma20_gap": np.nan,
                    "macd": np.nan,
                    "atr": np.nan,
                    "volume_change_rate": np.nan,
                }
            )
            prediction_id += 1
    return pd.DataFrame(records)


def test_training_dataset_uses_only_historical_replay_and_whitelisted_features(db):
    stock = add_stock(db)
    add_prediction(
        db,
        stock,
        source="historical_replay",
        prediction_date=date(2025, 1, 2),
    )
    add_prediction(
        db,
        stock,
        source="live",
        prediction_date=date(2025, 1, 3),
    )
    db.commit()

    frame, metadata = build_ml_dataset(db)

    assert len(frame) == 1
    assert metadata["source"] == "historical_replay"
    assert "future_close" not in frame.columns
    assert "actual_return" not in CORE_FEATURES
    assert frame.iloc[0]["direction_target"] == 1


def test_chronological_split_has_no_shuffle_or_overlapping_dates():
    split = chronological_split(synthetic_dataset())
    train_dates = set(split["train"]["prediction_date"])
    calibration_dates = set(split["calibration"]["prediction_date"])
    test_dates = set(split["test"]["prediction_date"])

    assert train_dates.isdisjoint(calibration_dates)
    assert train_dates.isdisjoint(test_dates)
    assert calibration_dates.isdisjoint(test_dates)
    assert max(train_dates) < min(calibration_dates) < min(test_dates)
    assert split["train"]["prediction_date"].is_monotonic_increasing


def test_insufficient_samples_do_not_create_ml_model(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ml_model_service, "MODEL_DIR", tmp_path)
    result = train_ml_candidates(db)

    assert result["status"] == "insufficient"
    assert db.scalars(
        select(ModelVersion).where(ModelVersion.model_type != "baseline")
    ).all() == []


def test_candidate_artifacts_remain_inactive_until_user_applies(
    db,
    tmp_path,
    monkeypatch,
):
    frame = synthetic_dataset()
    monkeypatch.setattr(ml_model_service, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(
        ml_model_service,
        "build_ml_dataset",
        lambda _db: (
            frame,
            {
                "source": "historical_replay",
                "total_historical_rows": len(frame),
                "usable_direction_rows": len(frame),
                "flat_excluded": 0,
                "invalid_feature_snapshot_excluded": 0,
            },
        ),
    )
    monkeypatch.setattr(
        ml_model_service,
        "_monthly_walk_forward",
        lambda *_args, **_kwargs: {
            "months": [],
            "month_count": 9,
            "accuracy_std": 0.02,
            "worst_accuracy": 80.0,
            "stable": True,
        },
    )

    result = train_ml_candidates(db)
    ml_versions = list(
        db.scalars(
            select(ModelVersion).where(ModelVersion.model_type != "baseline")
        ).all()
    )
    classifier_candidates = [
        version
        for version in ml_versions
        if version.status == "candidate"
        and version.model_type != "hist_gradient_boosting_regressor"
    ]

    assert result["status"] == "completed"
    assert classifier_candidates
    assert all(version.is_active is False for version in ml_versions)
    for version in ml_versions:
        assert version.artifact_path
        assert version.metadata_path
        assert tmp_path.joinpath(f"{version.version_name}.joblib").exists()
        assert tmp_path.joinpath(f"{version.version_name}.json").exists()
        metadata = json.loads(
            tmp_path.joinpath(f"{version.version_name}.json").read_text(encoding="utf-8")
        )
        assert metadata["is_active"] is False

    baseline = active_model_version(db)
    db.commit()
    assert baseline.model_type == "baseline"

    selected = classifier_candidates[0]
    baseline_prediction = RuleBasedPredictionModel().predict(60, 30, 200)
    before = predict_with_active_model(
        db,
        live_features={
            key: 0.0 for key in json.loads(selected.feature_schema_json)
        },
        baseline_prediction=baseline_prediction,
    )
    assert before["model_version"] == RuleBasedPredictionModel.version

    activate_model(db, selected.id)
    after = predict_with_active_model(
        db,
        live_features={
            key: (50.0 if key == "technical_score" else 0.0)
            for key in json.loads(selected.feature_schema_json)
        },
        baseline_prediction=baseline_prediction,
    )
    assert after["model_version"] == selected.version_name
    assert db.get(ModelVersion, selected.id).is_active is True

    restore_baseline_model(db)
    assert active_model_version(db).model_type == "baseline"
