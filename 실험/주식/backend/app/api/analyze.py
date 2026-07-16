from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import AnalysisJob, Holding, Stock
from app.services.analysis_runner import analyze_stock, run_analysis
from app.services.job_manager import (
    cancel_analysis_job as cancel_job,
    create_analysis_job,
    reconcile_analysis_jobs,
    serialize_job,
)
from app.utils.logger import get_logger

router = APIRouter(prefix="/analyze", tags=["analysis"])
logger = get_logger(__name__)


class AnalysisRequest(BaseModel):
    market: str = "ALL"
    include_recommendations: bool = True
    include_holdings: bool = True


@router.post("/run")
def analyze(payload: AnalysisRequest, db: Session = Depends(get_db)) -> dict:
    """Synchronous compatibility endpoint used by tests and manual API clients."""
    holdings = db.scalars(
        select(Holding)
        .options(joinedload(Holding.stock))
        .where(Holding.is_active.is_(True))
    ).all()
    if payload.market != "ALL":
        holdings = [holding for holding in holdings if holding.market_type == payload.market]
    return run_analysis(
        db,
        list(holdings),
        include_recommendations=payload.include_recommendations,
        include_holdings=payload.include_holdings,
    )


@router.post("/jobs")
def start_analysis_job(payload: AnalysisRequest) -> dict:
    job_id = create_analysis_job(
        market=payload.market,
        include_recommendations=payload.include_recommendations,
        include_holdings=payload.include_holdings,
    )
    return {"success": True, "job_id": job_id, "message": "백그라운드 분석을 시작했습니다."}


@router.get("/jobs")
def list_analysis_jobs(db: Session = Depends(get_db)) -> list[dict]:
    reconcile_analysis_jobs(db)
    rows = db.scalars(select(AnalysisJob).order_by(AnalysisJob.created_at.desc()).limit(20)).all()
    return [serialize_job(row) for row in rows]


@router.get("/jobs/{job_id}")
def get_analysis_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    reconcile_analysis_jobs(db)
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    return serialize_job(job)


@router.post("/jobs/{job_id}/cancel")
def cancel_analysis_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = cancel_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    return serialize_job(job)


@router.post("/ticker/{ticker}")
def analyze_ticker(ticker: str, db: Session = Depends(get_db)) -> dict:
    normalized = ticker.strip().upper()
    stock = db.scalar(select(Stock).where(Stock.ticker == normalized))
    if not stock and normalized.isdigit() and len(normalized) == 6:
        stock = db.scalar(select(Stock).where(Stock.ticker.in_([f"{normalized}.KS", f"{normalized}.KQ"])))
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 먼저 추가해 주세요.")
    try:
        result = analyze_stock(db, stock)
        db.commit()
        report = result["report"]
        return {
            "success": True,
            "ticker": stock.ticker,
            "report_id": report.id,
            "data_available": report.current_price is not None,
            "message": (
                "종목 분석이 완료되었습니다."
                if report.current_price is not None
                else "분석은 완료됐지만 가격 데이터를 찾지 못했습니다. 티커와 시장을 확인해 주세요."
            ),
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Single stock analysis failed for %s", ticker)
        raise HTTPException(status_code=502, detail=f"종목 데이터 수집에 실패했습니다: {exc}") from exc
