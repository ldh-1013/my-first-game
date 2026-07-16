from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from shutil import copy2

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import database_path, engine, get_db
from app.models import DailyPrice, DailyReport, NewsArticle, PredictionResult, Recommendation, Stock

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


def _backup_dir() -> Path:
    path = database_path()
    if path is None:
        raise HTTPException(status_code=400, detail="SQLite 데이터베이스에서만 지원됩니다.")
    target = path.parent / "backups"
    target.mkdir(parents=True, exist_ok=True)
    return target


@router.post("/backup")
def create_backup() -> dict:
    source = database_path()
    if source is None or not source.exists():
        raise HTTPException(status_code=404, detail="데이터베이스 파일을 찾을 수 없습니다.")
    filename = f"stock_insight_{datetime.now():%Y%m%d_%H%M%S}.db"
    destination = _backup_dir() / filename
    with sqlite3.connect(source) as source_db, sqlite3.connect(destination) as backup_db:
        source_db.backup(backup_db)
    return {"success": True, "filename": filename, "size": destination.stat().st_size}


@router.get("/backups")
def list_backups() -> list[dict]:
    return [
        {
            "filename": item.name,
            "size": item.stat().st_size,
            "modified_at": datetime.fromtimestamp(item.stat().st_mtime),
        }
        for item in sorted(_backup_dir().glob("*.db"), key=lambda row: row.stat().st_mtime, reverse=True)
    ]


@router.post("/restore/{filename}")
def restore_backup(filename: str) -> dict:
    safe_name = Path(filename).name
    backup = _backup_dir() / safe_name
    target = database_path()
    if not backup.exists() or target is None:
        raise HTTPException(status_code=404, detail="백업 파일을 찾을 수 없습니다.")
    emergency = _backup_dir() / f"before_restore_{datetime.now():%Y%m%d_%H%M%S}.db"
    copy2(target, emergency)
    engine.dispose()
    with sqlite3.connect(backup) as backup_db, sqlite3.connect(target) as target_db:
        backup_db.backup(target_db)
    return {
        "success": True,
        "restored": safe_name,
        "emergency_backup": emergency.name,
        "message": "복원이 완료되었습니다. 앱을 다시 실행해 주세요.",
    }


@router.post("/cleanup")
def cleanup_database(
    keep_days: int = Query(default=730, ge=90, le=3650),
    db: Session = Depends(get_db),
) -> dict:
    cutoff = date.today() - timedelta(days=keep_days)
    counts = {}
    for name, model, condition in [
        ("daily_prices", DailyPrice, DailyPrice.date < cutoff),
        ("daily_reports", DailyReport, DailyReport.report_date < cutoff),
        ("recommendations", Recommendation, Recommendation.report_date < cutoff),
        ("predictions", PredictionResult, PredictionResult.prediction_date < cutoff),
    ]:
        result = db.execute(delete(model).where(condition))
        counts[name] = result.rowcount or 0
    news_cutoff = datetime.now() - timedelta(days=keep_days)
    result = db.execute(delete(NewsArticle).where(NewsArticle.published_at < news_cutoff))
    counts["news"] = result.rowcount or 0
    db.commit()
    return {"success": True, "cutoff": cutoff, "deleted": counts}


@router.get("/reports.csv")
def export_reports_csv(db: Session = Depends(get_db)) -> Response:
    rows = db.scalars(
        select(DailyReport).order_by(DailyReport.report_date.desc(), DailyReport.final_score.desc())
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "date",
            "ticker",
            "name",
            "price",
            "change_rate",
            "score",
            "up_probability",
            "confidence",
            "decision",
            "surge_warning",
        ]
    )
    for row in rows:
        stock = db.get(Stock, row.stock_id)
        writer.writerow(
            [
                row.report_date,
                stock.ticker,
                stock.name,
                row.current_price,
                row.change_rate,
                row.final_score,
                row.up_probability,
                row.confidence_level,
                row.decision_status,
                row.surge_warning,
            ]
        )
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="stock-insight-reports.csv"'},
    )
