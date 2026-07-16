from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import AnalysisJob, FinancialSnapshot, Stock
from app.services import analysis_runner, financial_service
from app.services.job_manager import (
    cancel_analysis_job,
    reconcile_analysis_jobs,
)


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


def test_cancel_marks_running_job_finished_immediately(db):
    job = AnalysisJob(
        status="running",
        total_items=10,
        completed_items=4,
        current_ticker="STUCK",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    cancelled = cancel_analysis_job(db, job.id)

    assert cancelled is not None
    assert cancelled.status == "cancelled"
    assert cancelled.cancel_requested is True
    assert cancelled.current_ticker is None
    assert cancelled.finished_at is not None


def test_reconcile_marks_orphaned_old_job_failed(db):
    job = AnalysisJob(
        status="running",
        total_items=74,
        completed_items=73,
        current_ticker="042700.KS",
        started_at=datetime.utcnow() - timedelta(minutes=10),
    )
    db.add(job)
    db.commit()

    repaired = reconcile_analysis_jobs(db)
    db.refresh(job)

    assert repaired == 1
    assert job.status == "failed"
    assert job.current_ticker is None
    assert job.finished_at is not None


def test_cancel_is_checked_again_after_stock_finishes(db, monkeypatch):
    stock = Stock(
        ticker="TEST",
        name="TEST",
        market="US",
        country="US",
        currency="USD",
        is_listed=True,
    )
    db.add(stock)
    db.commit()
    monkeypatch.setattr(analysis_runner, "_ensure_stock", lambda *_args: stock)
    monkeypatch.setattr(
        analysis_runner,
        "analyze_stock",
        lambda *_args: {"stock": stock, "report": object()},
    )

    calls = []

    def progress(completed, failed, ticker, errors):
        calls.append((completed, failed, ticker, errors))
        return completed == 1

    result = analysis_runner.run_analysis_items(
        db,
        [{"ticker": "TEST"}],
        include_recommendations=False,
        progress_callback=progress,
    )

    assert result["cancelled"] is True
    assert result["analyzed"] == 1
    assert calls[-1][0] == 1


def test_financial_timeout_returns_latest_stored_snapshot(db, monkeypatch):
    stock = Stock(
        ticker="TIMEOUT",
        name="TIMEOUT",
        market="US",
        country="US",
        currency="USD",
        is_listed=True,
    )
    db.add(stock)
    db.flush()
    stored = FinancialSnapshot(
        stock_id=stock.id,
        as_of_date=date.today() - timedelta(days=1),
        revenue=123,
    )
    db.add(stored)
    db.commit()

    class TimedOutFuture:
        def result(self, timeout):
            del timeout
            raise financial_service.TimeoutError

        def cancel(self):
            return True

    class TimedOutExecutor:
        def submit(self, *_args, **_kwargs):
            return TimedOutFuture()

    monkeypatch.setattr(
        financial_service,
        "_financial_executor",
        TimedOutExecutor(),
    )

    result = financial_service.collect_financial_snapshot(db, stock)

    assert result is not None
    assert result.id == stored.id
