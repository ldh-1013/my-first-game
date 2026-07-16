import json
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (
    FinancialSnapshot,
    HistoricalReplayRun,
    PredictionResult,
    Stock,
)
from app.services.backtest_service import (
    absolute_forecast_error,
    candidate_model_summary,
    direction_hit,
    range_hit_for_return,
)
from app.services.historical_replay_service import (
    HistoricalContext,
    build_prediction_for_date,
    ensure_daily_validation_run,
    next_trading_outcome,
    reconcile_historical_replay_runs,
    replay_universe,
    run_historical_replay,
)
from app.services.quality_service import calibration_snapshot, confidence_from_history


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


def price_frame(rows: int = 100, end: date | None = None) -> pd.DataFrame:
    index = pd.bdate_range(end=end or date.today(), periods=rows)
    close = np.linspace(100, 120, rows)
    return pd.DataFrame(
        {
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": np.linspace(1000, 3000, rows),
        },
        index=index,
    )


def stock_row(db: Session, ticker: str = "TEST", market: str = "US") -> Stock:
    stock = Stock(
        ticker=ticker,
        name=ticker,
        market=market,
        country=market,
        currency="KRW" if market == "KR" else "USD",
        is_listed=True,
        asset_type="LISTED_STOCK",
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


def prediction_row(
    stock_id: int,
    prediction_date: date,
    *,
    source: str = "historical_replay",
    raw_probability: float = 72,
    actual_direction: str = "up",
    is_correct: bool = True,
) -> PredictionResult:
    return PredictionResult(
        stock_id=stock_id,
        prediction_date=prediction_date,
        target_date=prediction_date + timedelta(days=1),
        final_score=65,
        up_probability=raw_probability,
        down_probability=100 - raw_probability,
        expected_range_low=-2,
        expected_range_high=3,
        confidence_level="low",
        model_version="rule-based-v2-calibrated",
        horizon_days=1,
        prediction_source=source,
        raw_up_probability=raw_probability,
        calibrated_up_probability=raw_probability,
        actual_return=1 if actual_direction == "up" else -1,
        actual_direction=actual_direction,
        is_correct=is_correct,
        range_hit=True,
        absolute_error=0.5,
    )


def test_historical_prediction_never_passes_future_rows_to_indicators(
    db, monkeypatch
):
    from app.services import historical_replay_service

    stock = stock_row(db)
    frame = price_frame(20)
    as_of_date = pd.Timestamp(frame.index[9]).date()
    observed = {}
    real_calculate = historical_replay_service.calculate_indicators

    def guarded_calculate(sliced):
        observed["max_date"] = pd.Timestamp(sliced.index.max()).date()
        return real_calculate(sliced)

    monkeypatch.setattr(
        historical_replay_service,
        "calculate_indicators",
        guarded_calculate,
    )
    build_prediction_for_date(db, stock, frame, as_of_date)
    assert observed["max_date"] == as_of_date


def test_next_trading_return_uses_actual_next_market_row():
    frame = pd.DataFrame(
        {
            "close": [100.0, 103.0],
        },
        index=pd.to_datetime(["2026-06-19", "2026-06-22"]),
    )
    target_date, actual_return = next_trading_outcome(
        frame,
        date(2026, 6, 19),
    )
    assert target_date == date(2026, 6, 22)
    assert actual_return == pytest.approx(3.0)


@pytest.mark.parametrize("ticker,market", [("005930.KS", "KR"), ("NVDA", "US")])
def test_kr_and_us_both_use_their_own_next_available_trading_row(
    ticker,
    market,
):
    frame = pd.DataFrame(
        {"close": [100.0, 99.0]},
        index=pd.to_datetime(["2026-06-18", "2026-06-22"]),
    )
    target_date, _ = next_trading_outcome(frame, date(2026, 6, 18))
    assert ticker
    assert market in {"KR", "US"}
    assert target_date == date(2026, 6, 22)


def test_private_stock_is_excluded_from_replay_universe(db):
    private = Stock(
        ticker="SPACEX",
        name="SpaceX",
        market="US",
        country="US",
        currency="USD",
        is_listed=False,
        asset_type="PRIVATE",
    )
    db.add(private)
    db.commit()
    tickers = {stock.ticker for stock in replay_universe(db, ["US"])}
    assert "SPACEX" not in tickers


def test_replay_does_not_call_current_news_rss(db, monkeypatch):
    from app.services import news_collector

    stock = stock_row(db)
    called = False

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("current RSS must not be used")

    monkeypatch.setattr(news_collector, "fetch_news_for_ticker", forbidden)
    result = build_prediction_for_date(
        db,
        stock,
        price_frame(30),
        date.today(),
        historical_context=HistoricalContext(news=[], financials=[]),
    )
    assert called is False
    assert result["historical_news_available"] is False
    assert result["feature_snapshot"]["news_score"] == 0


def test_future_financial_snapshot_is_not_used_for_past_replay(db):
    stock = stock_row(db)
    snapshot = FinancialSnapshot(
        stock_id=stock.id,
        as_of_date=date.today(),
        return_on_equity=0.5,
        earnings_growth=0.5,
    )
    result = build_prediction_for_date(
        db,
        stock,
        price_frame(30, end=date.today() - timedelta(days=30)),
        date.today() - timedelta(days=30),
        historical_context=HistoricalContext(news=[], financials=[snapshot]),
    )
    assert result["historical_financial_available"] is False
    assert result["feature_snapshot"]["financial_score"] == 0


def test_repeated_replay_does_not_duplicate_and_preserves_live_rows(
    db,
    monkeypatch,
):
    from app.services import historical_replay_service

    stock = stock_row(db)
    frame = price_frame(80)
    live_date = pd.Timestamp(frame.index[-2]).date()
    db.add(prediction_row(stock.id, live_date, source="live"))
    db.commit()
    monkeypatch.setattr(
        historical_replay_service,
        "fetch_daily_prices",
        lambda *_args, **_kwargs: frame.copy(),
    )
    monkeypatch.setattr(
        historical_replay_service,
        "replay_candidates",
        lambda *_args, **_kwargs: [stock],
    )

    def make_run():
        run = HistoricalReplayRun(
            start_date=pd.Timestamp(frame.index[-20]).date(),
            end_date=date.today(),
            market_scope="US",
            horizon_days=1,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    run_historical_replay(db, make_run())
    first_count = db.scalar(
        select(func.count(PredictionResult.id)).where(
            PredictionResult.prediction_source == "historical_replay"
        )
    )
    run_historical_replay(db, make_run())
    second_count = db.scalar(
        select(func.count(PredictionResult.id)).where(
            PredictionResult.prediction_source == "historical_replay"
        )
    )
    live_count = db.scalar(
        select(func.count(PredictionResult.id)).where(
            PredictionResult.prediction_source == "live"
        )
    )
    assert first_count > 0
    assert second_count == first_count
    assert live_count == 1


def test_daily_validation_refresh_starts_when_today_is_missing(db, monkeypatch):
    from app.services import historical_replay_service

    class NoopExecutor:
        def submit(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(historical_replay_service, "_executor", NoopExecutor())
    today = date(2026, 6, 27)
    old_run = HistoricalReplayRun(
        start_date=today - timedelta(days=730),
        end_date=today - timedelta(days=1),
        market_scope="KR,US",
        horizon_days=1,
        status="completed",
        progress_stage="completed",
        created_at=datetime(2026, 6, 26, 9, 0, 0),
    )
    db.add(old_run)
    db.commit()

    run, created, reason = ensure_daily_validation_run(db, today=today)

    assert created is True
    assert reason == "started"
    assert run.end_date == today
    assert run.market_scope == "KR,US"


def test_daily_validation_refresh_does_not_duplicate_today(db, monkeypatch):
    from app.services import historical_replay_service

    class NoopExecutor:
        def submit(self, *_args, **_kwargs):
            raise AssertionError("fresh daily validation must not start twice")

    monkeypatch.setattr(historical_replay_service, "_executor", NoopExecutor())
    today = date(2026, 6, 27)
    run = HistoricalReplayRun(
        start_date=today - timedelta(days=730),
        end_date=today,
        market_scope="KR,US",
        horizon_days=1,
        status="completed",
        progress_stage="completed",
        created_at=datetime(2026, 6, 27, 9, 0, 0),
    )
    db.add(run)
    db.commit()

    latest, created, reason = ensure_daily_validation_run(db, today=today)

    assert created is False
    assert reason == "already_refreshed_today"
    assert latest.id == run.id


def test_daily_validation_refresh_does_not_overlap_running_run(db, monkeypatch):
    from app.services import historical_replay_service

    class NoopExecutor:
        def submit(self, *_args, **_kwargs):
            raise AssertionError("running daily validation must not overlap")

    monkeypatch.setattr(historical_replay_service, "_executor", NoopExecutor())
    today = date(2026, 6, 27)
    now = datetime.now(UTC).replace(tzinfo=None)
    run = HistoricalReplayRun(
        start_date=today - timedelta(days=730),
        end_date=today,
        market_scope="KR,US",
        horizon_days=1,
        status="running",
        progress_stage="replaying",
        created_at=now,
        started_at=now,
    )
    db.add(run)
    db.commit()

    latest, created, reason = ensure_daily_validation_run(db, today=today)

    assert created is False
    assert reason == "already_running"
    assert latest.id == run.id


def test_reconcile_historical_replay_marks_orphaned_run_failed(db):
    run = HistoricalReplayRun(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 27),
        market_scope="KR,US",
        horizon_days=1,
        status="running",
        progress_stage="replaying",
        current_ticker="NVDA",
        current_date=date(2026, 6, 26),
        created_at=datetime(2026, 6, 27, 8, 0, 0),
        started_at=datetime(2026, 6, 27, 8, 1, 0),
    )
    db.add(run)
    db.commit()

    repaired = reconcile_historical_replay_runs(db, assume_orphaned=True)
    db.refresh(run)

    assert repaired == 1
    assert run.status == "failed"
    assert run.progress_stage == "failed"
    assert run.current_ticker is None
    assert run.completed_at is not None


def test_same_prediction_date_does_not_learn_another_stocks_future_outcome(
    db,
    monkeypatch,
):
    from app.services import historical_replay_service

    first = stock_row(db, "FIRST")
    second = stock_row(db, "SECOND")
    frame = price_frame(40)
    monkeypatch.setattr(
        historical_replay_service,
        "fetch_daily_prices",
        lambda *_args, **_kwargs: frame.copy(),
    )
    monkeypatch.setattr(
        historical_replay_service,
        "replay_candidates",
        lambda *_args, **_kwargs: [first, second],
    )
    run = HistoricalReplayRun(
        start_date=pd.Timestamp(frame.index[-5]).date(),
        end_date=date.today(),
        market_scope="US",
        horizon_days=1,
    )
    db.add(run)
    db.commit()
    run_historical_replay(db, run)
    earliest = db.scalar(
        select(func.min(PredictionResult.prediction_date)).where(
            PredictionResult.prediction_source == "historical_replay"
        )
    )
    rows = list(
        db.scalars(
            select(PredictionResult).where(
                PredictionResult.prediction_source == "historical_replay",
                PredictionResult.prediction_date == earliest,
            )
        ).all()
    )
    assert len(rows) == 2
    assert {
        json.loads(row.feature_snapshot)["calibration_samples"] for row in rows
    } == {0}


def test_direction_range_and_absolute_error_rules():
    assert direction_hit(60, 1.2) is True
    assert direction_hit(40, -1.2) is True
    assert direction_hit(60, 0) is None
    assert range_hit_for_return(-1.5, 2.5, 1.2) is True
    assert range_hit_for_return(-1.5, 2.5, 3.7) is False
    assert absolute_forecast_error(-1.5, 2.5, 1.2) == pytest.approx(0.7)


def test_probability_bucket_calibration_uses_observed_replay_rate(db):
    stock = stock_row(db)
    start = date.today() - timedelta(days=150)
    for index in range(100):
        is_up = index < 60
        db.add(
            prediction_row(
                stock.id,
                start + timedelta(days=index),
                raw_probability=72,
                actual_direction="up" if is_up else "down",
                is_correct=is_up,
            )
        )
    db.commit()
    result = calibration_snapshot(db, 74, market="US")
    assert result["sample_count"] == 100
    assert result["observed_up_rate"] == 60
    assert 60 < result["calibrated_probability"] < 74


def test_insufficient_replay_samples_cannot_raise_confidence(db):
    result = confidence_from_history(
        db,
        market="US",
        raw_probability=75,
        base_confidence="medium",
        data_quality=100,
        volatility=15,
        news_available=True,
        financial_available=True,
    )
    assert result["sample_count"] == 0
    assert result["level"] == "very_low"


def test_weight_candidate_is_never_auto_applied(db):
    stock = stock_row(db)
    rows = []
    start = date.today() - timedelta(days=800)
    for index in range(400):
        row = prediction_row(
            stock.id,
            start + timedelta(days=index * 2),
            actual_direction="up" if index % 2 == 0 else "down",
            is_correct=index % 2 == 0,
        )
        row.feature_snapshot = json.dumps(
            {
                "technical_score": 30 if index % 2 == 0 else -30,
                "volume_score": 20 if index % 3 == 0 else -10,
                "news_score": 0,
                "financial_score": 0,
                "risk_score": 20,
            }
        )
        rows.append(row)
    result = candidate_model_summary(db, rows)
    assert result["training_samples"] >= 100
    assert result["validation_samples"] >= 100
    assert result["applied"] is False
