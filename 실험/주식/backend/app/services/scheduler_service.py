from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Setting
from app.services.historical_replay_service import ensure_daily_validation_run
from app.services.job_manager import create_analysis_job
from app.utils.logger import get_logger

logger = get_logger(__name__)
_scheduler = BackgroundScheduler(timezone="Asia/Seoul")
ANALYSIS_JOB_ID = "daily-stock-analysis"
VALIDATION_JOB_ID = "daily-prediction-validation"


def _settings() -> dict[str, str]:
    with SessionLocal() as db:
        return {row.key: row.value for row in db.scalars(select(Setting)).all()}


def configure_scheduler() -> dict:
    settings = _settings()
    enabled = settings.get("schedule_enabled", "false").lower() == "true"
    time_value = settings.get("collection_time", "08:30")
    market = settings.get("default_market", "ALL")
    try:
        hour, minute = [int(part) for part in time_value.split(":", 1)]
    except (TypeError, ValueError):
        hour, minute = 8, 30
    if _scheduler.get_job(ANALYSIS_JOB_ID):
        _scheduler.remove_job(ANALYSIS_JOB_ID)
    if enabled:
        _scheduler.add_job(
            lambda: create_analysis_job(market=market),
            CronTrigger(hour=hour, minute=minute, timezone="Asia/Seoul"),
            id=ANALYSIS_JOB_ID,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
    _configure_validation_job(settings)
    if not _scheduler.running:
        _scheduler.start()
    return scheduler_status()


def _configure_validation_job(settings: dict[str, str]) -> None:
    enabled = settings.get("validation_schedule_enabled", "true").lower() == "true"
    time_value = settings.get("validation_time", "18:10")
    try:
        hour, minute = [int(part) for part in time_value.split(":", 1)]
    except (TypeError, ValueError):
        hour, minute = 18, 10
    if _scheduler.get_job(VALIDATION_JOB_ID):
        _scheduler.remove_job(VALIDATION_JOB_ID)
    if enabled:
        _scheduler.add_job(
            _run_daily_prediction_validation,
            CronTrigger(hour=hour, minute=minute, timezone="Asia/Seoul"),
            id=VALIDATION_JOB_ID,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )


def _run_daily_prediction_validation() -> None:
    with SessionLocal() as db:
        run, created, reason = ensure_daily_validation_run(db)
        logger.info(
            "Daily prediction validation %s: run_id=%s status=%s",
            reason,
            run.id,
            "created" if created else run.status,
        )


def scheduler_status() -> dict:
    job = _scheduler.get_job(ANALYSIS_JOB_ID) if _scheduler.running else None
    validation_job = _scheduler.get_job(VALIDATION_JOB_ID) if _scheduler.running else None
    return {
        "running": _scheduler.running,
        "enabled": job is not None,
        "next_run_time": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "timezone": "Asia/Seoul",
        "analysis": {
            "enabled": job is not None,
            "next_run_time": (
                job.next_run_time.isoformat() if job and job.next_run_time else None
            ),
        },
        "prediction_validation": {
            "enabled": validation_job is not None,
            "next_run_time": (
                validation_job.next_run_time.isoformat()
                if validation_job and validation_job.next_run_time
                else None
            ),
            "timezone": "Asia/Seoul",
        },
    }


def shutdown_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
