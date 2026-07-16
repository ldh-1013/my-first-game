from datetime import date, timedelta

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.ensemble.dynamic_ensemble import combine_probabilities, fit_regime_weights
from app.evaluation.performance import (
    select_confidence_threshold,
    selective_signal_metrics,
)
from app.feature_engineering.point_in_time import build_point_in_time_feature_map
from app.market_regime.classifier import classify_market_regime
from app.models import DailyPrice, Stock


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


def test_point_in_time_features_do_not_change_when_future_price_changes(db):
    stock = Stock(
        ticker="PIT",
        name="PIT",
        market="US",
        country="US",
        currency="USD",
        is_listed=True,
    )
    db.add(stock)
    db.flush()
    start = date(2026, 1, 1)
    for index in range(35):
        close = 100 + index
        db.add(
            DailyPrice(
                stock_id=stock.id,
                date=start + timedelta(days=index),
                close_price=close,
                volume=1000 + index,
                trading_value=close * (1000 + index),
                ma5=close - 2,
                ma20=close - 8,
                atr=2,
                volatility_20d=30,
                volume_change_rate=5,
            )
        )
    db.commit()
    prediction_date = start + timedelta(days=30)
    end_date = start + timedelta(days=34)
    before = build_point_in_time_feature_map(
        db,
        start_date=prediction_date,
        end_date=end_date,
    )[(stock.id, prediction_date)]
    future = db.query(DailyPrice).filter_by(
        stock_id=stock.id,
        date=end_date,
    ).one()
    future.close_price = 10000
    future.trading_value = 999999999
    db.commit()
    after = build_point_in_time_feature_map(
        db,
        start_date=prediction_date,
        end_date=end_date,
    )[(stock.id, prediction_date)]
    assert after == before


def test_regime_classifier_covers_bull_bear_and_sideways():
    assert classify_market_regime(5, 0.7, 20) == "bull_low_vol"
    assert classify_market_regime(-5, 0.3, 55) == "bear_high_vol"
    assert classify_market_regime(0.2, 0.5, 20) == "sideways_low_vol"


def test_confidence_threshold_is_selected_from_supplied_calibration_only():
    targets = np.array([1] * 80 + [0] * 20)
    probabilities = np.array([0.8] * 80 + [0.2] * 20)
    returns = np.array([2.0] * 80 + [-2.0] * 20)
    result = select_confidence_threshold(
        targets,
        probabilities,
        returns,
        minimum_signals=20,
    )
    assert result["selection_source"] == "calibration_only"
    assert result["selected_threshold"] in {0.55, 0.60, 0.65, 0.70, 0.75, 0.80}


def test_selective_signal_metrics_apply_costs_and_drawdown():
    metrics = selective_signal_metrics(
        np.array([1, 0, 1, 0]),
        np.array([0.9, 0.1, 0.9, 0.1]),
        np.array([1.0, -1.0, -2.0, 1.0]),
        threshold=0.8,
        transaction_cost_percent=0.2,
    )
    assert metrics["trades"] == 4
    assert metrics["average_net_return"] < metrics["average_gross_return"]
    assert metrics["maximum_drawdown"] <= 0


def test_dynamic_ensemble_weights_are_normalized_and_regime_aware():
    targets = np.array([1, 1, 0, 0, 1, 0])
    regimes = np.array(["bull", "bull", "bear", "bear", "bull", "bear"])
    components = {
        "trend": np.array([0.8, 0.7, 0.4, 0.3, 0.8, 0.2]),
        "defensive": np.array([0.6, 0.55, 0.2, 0.1, 0.6, 0.2]),
    }
    weights = fit_regime_weights(
        targets,
        components,
        regimes,
        minimum_segment_samples=2,
    )
    assert sum(weights["global"].values()) == pytest.approx(1)
    assert sum(weights["bull"].values()) == pytest.approx(1)
    combined = combine_probabilities(components, regimes, weights)
    assert len(combined) == len(targets)
    assert np.all((combined > 0) & (combined < 1))


def test_research_and_empty_diagnostics_endpoints(client):
    research = client.get("/analytics/research")
    diagnostics = client.get("/analytics/performance/diagnostics")
    assert research.status_code == 200
    assert len(research.json()["references"]) >= 5
    assert diagnostics.status_code == 200
    assert diagnostics.json()["status"] == "insufficient"
