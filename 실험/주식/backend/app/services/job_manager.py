from __future__ import annotations

import json
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import AnalysisJob, Holding
from app.services.alert_service import create_portfolio_alerts
from app.services.analysis_runner import build_analysis_universe, run_analysis_items
from app.utils.logger import get_logger

logger = get_logger(__name__)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="stock-analysis")
_futures: dict[int, Future] = {}
STALE_JOB_GRACE = timedelta(minutes=5)


def create_analysis_job(
    market: str = "ALL",
    include_recommendations: bool = True,
    include_holdings: bool = True,
) -> int:
    with SessionLocal() as db:
        reconcile_analysis_jobs(db)
        active = db.scalar(
            select(AnalysisJob)
            .where(AnalysisJob.status.in_(["queued", "running"]))
            .order_by(AnalysisJob.created_at.desc())
        )
        if active and _future_is_active(active.id):
            return active.id

        holdings = db.scalars(
            select(Holding)
            .options(joinedload(Holding.stock))
            .where(Holding.is_active.is_(True))
        ).all()
        if market != "ALL":
            holdings = [
                holding for holding in holdings if holding.market_type == market
            ]
        items = build_analysis_universe(
            list(holdings),
            include_recommendations=include_recommendations,
            include_holdings=include_holdings,
        )
        job = AnalysisJob(
            status="queued",
            market=market,
            total_items=len(items),
            message="분석 대기 중",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    future = _executor.submit(
        _run_job,
        job_id,
        items,
        include_recommendations,
    )
    _futures[job_id] = future
    future.add_done_callback(lambda _future, value=job_id: _futures.pop(value, None))
    return job_id


def _run_job(job_id: int, items: list[dict], include_recommendations: bool) -> None:
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if not job:
            return
        try:
            if job.cancel_requested or job.status == "cancelled":
                _mark_cancelled(job)
                db.commit()
                return
            job.status = "running"
            job.started_at = datetime.utcnow()
            job.message = "종목 분석을 시작했습니다."
            db.commit()

            def progress(
                completed: int,
                failed: int,
                ticker: str,
                errors: list[dict],
            ) -> bool:
                db.refresh(job)
                if job.cancel_requested or job.status == "cancelled":
                    return True
                job.completed_items = completed
                job.failed_items = failed
                job.current_ticker = ticker
                job.message = f"{ticker} 분석 중"
                job.error_details = json.dumps(errors[-20:], ensure_ascii=False)
                db.commit()
                return False

            result = run_analysis_items(
                db,
                items,
                include_recommendations=include_recommendations,
                progress_callback=progress,
            )
            db.refresh(job)
            job.completed_items = result["analyzed"]
            job.failed_items = result["failed"]
            job.current_ticker = None
            job.finished_at = datetime.utcnow()
            if result.get("cancelled") or job.cancel_requested or job.status == "cancelled":
                _mark_cancelled(job)
            else:
                job.status = "completed"
                job.message = (
                    f"분석 완료 · 성공 {result['analyzed']} · 실패 {result['failed']}"
                )
            job.error_details = json.dumps(result["errors"], ensure_ascii=False)
            db.commit()
            if job.status == "completed":
                try:
                    create_portfolio_alerts(db)
                except Exception:
                    db.rollback()
                    logger.exception(
                        "Portfolio alert generation failed after analysis job %s",
                        job_id,
                    )
        except Exception as exc:
            db.rollback()
            logger.exception("Analysis job %s failed", job_id)
            failed_job = db.get(AnalysisJob, job_id)
            if not failed_job:
                return
            if failed_job.cancel_requested or failed_job.status == "cancelled":
                _mark_cancelled(failed_job)
            else:
                failed_ticker = failed_job.current_ticker
                failed_job.status = "failed"
                failed_job.current_ticker = None
                failed_job.finished_at = datetime.utcnow()
                failed_job.message = f"분석 작업 오류: {type(exc).__name__}"
                errors = _decode_errors(failed_job.error_details)
                errors.append(
                    {
                        "ticker": failed_ticker,
                        "error": str(exc),
                    }
                )
                failed_job.error_details = json.dumps(
                    errors[-20:],
                    ensure_ascii=False,
                )
            db.commit()


def cancel_analysis_job(db: Session, job_id: int) -> AnalysisJob | None:
    job = db.get(AnalysisJob, job_id)
    if not job:
        return None
    if job.status not in {"queued", "running"}:
        return job
    job.cancel_requested = True
    _mark_cancelled(job)
    db.commit()
    future = _futures.get(job_id)
    if future and not future.running():
        future.cancel()
    return job


def recover_analysis_jobs_on_startup() -> int:
    with SessionLocal() as db:
        return reconcile_analysis_jobs(db, force=True)


def reconcile_analysis_jobs(db: Session, *, force: bool = False) -> int:
    now = datetime.utcnow()
    repaired = 0
    jobs = db.scalars(
        select(AnalysisJob).where(AnalysisJob.status.in_(["queued", "running"]))
    ).all()
    for job in jobs:
        reference = job.started_at or job.created_at
        stale_by_age = reference is not None and now - reference >= STALE_JOB_GRACE
        future = _futures.get(job.id)
        worker_missing = future is None or future.done()
        if not force and not (worker_missing and stale_by_age):
            continue
        if job.cancel_requested:
            _mark_cancelled(job)
        else:
            job.status = "failed"
            job.current_ticker = None
            job.finished_at = now
            job.message = "서버 재시작 또는 작업 중단으로 분석이 종료되었습니다."
            errors = _decode_errors(job.error_details)
            errors.append(
                {
                    "ticker": None,
                    "error": "background_worker_interrupted",
                }
            )
            job.error_details = json.dumps(errors[-20:], ensure_ascii=False)
        repaired += 1
    if repaired:
        db.commit()
    return repaired


def serialize_job(job: AnalysisJob) -> dict:
    errors = _decode_errors(job.error_details)
    processed = job.completed_items + job.failed_items
    return {
        "id": job.id,
        "status": job.status,
        "market": job.market,
        "total_items": job.total_items,
        "completed_items": job.completed_items,
        "failed_items": job.failed_items,
        "processed_items": processed,
        "progress_percent": (
            round(processed / job.total_items * 100, 1)
            if job.total_items
            else 0
        ),
        "current_ticker": job.current_ticker,
        "message": job.message,
        "errors": errors,
        "cancel_requested": job.cancel_requested,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "created_at": job.created_at,
    }


def _future_is_active(job_id: int) -> bool:
    future = _futures.get(job_id)
    return bool(future and not future.done())


def _mark_cancelled(job: AnalysisJob) -> None:
    job.status = "cancelled"
    job.current_ticker = None
    job.finished_at = datetime.utcnow()
    job.message = "사용자 요청으로 분석을 중단했습니다."


def _decode_errors(value: str | None) -> list[dict]:
    try:
        decoded = json.loads(value or "[]")
        return decoded if isinstance(decoded, list) else []
    except (TypeError, json.JSONDecodeError):
        return []
