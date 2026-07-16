from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Recommendation, Stock
from app.schemas.recommendation_schema import RecommendationRead
from app.services.job_manager import create_analysis_job
from app.services.top5_service import rank_global_market

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _recommendation(row, stock: Stock, rank: int | None = None) -> RecommendationRead:
    return RecommendationRead(
        id=row.id,
        report_date=row.report_date,
        rank=rank or row.rank,
        stock_id=row.stock_id,
        ticker=stock.ticker,
        name=stock.name,
        market=stock.market,
        total_score=row.total_score,
        up_probability=row.up_probability,
        expected_range_low=row.expected_range_low,
        expected_range_high=row.expected_range_high,
        reason=row.reason,
        risk_summary=row.risk_summary,
        time_horizon=row.time_horizon,
        checklist=row.checklist,
        surge_warning=row.surge_warning,
        surge_reason=row.surge_reason,
    )


@router.get("/today", response_model=list[RecommendationRead])
def today_recommendations(db: Session = Depends(get_db)) -> list[RecommendationRead]:
    rows = db.scalars(
        select(Recommendation)
        .where(Recommendation.report_date == date.today())
        .order_by(Recommendation.rank)
    ).all()
    return [_recommendation(row, db.get(Stock, row.stock_id)) for row in rows]


@router.get("/top5", response_model=list[RecommendationRead])
def global_top5(db: Session = Depends(get_db)) -> list[RecommendationRead]:
    """Combined KR/US market ranking. Holdings are not consulted."""
    result = []
    for rank, row in enumerate(rank_global_market(db, limit=5), start=1):
        stock = row["stock"]
        result.append(
            RecommendationRead(
                id=stock.id,
                report_date=row["latest_date"],
                rank=rank,
                stock_id=stock.id,
                ticker=stock.ticker,
                name=stock.name,
                market=stock.market,
                total_score=row["ranking_score"],
                up_probability=row["up_probability"],
                expected_range_low=row["expected_range_low"],
                expected_range_high=row["expected_range_high"],
                reason=(
                    f"한국·미국 통합 시장 순위 · 상승 가능성 {row['up_probability']:.1f}% · "
                    f"최근 5거래일 {row['recent_5d_return']:+.2f}%"
                ),
                risk_summary=(
                    f"변동성 위험 점수 {row['risk_score']:.1f} · "
                    f"기술 점수 {row['technical_score']:.1f} · 거래량 점수 {row['volume_score']:.1f}"
                ),
                time_horizon="DAY 1~2 관찰",
                checklist="공시·뉴스 원문과 장중 거래량을 상세 분석에서 확인하세요.",
                surge_warning=row["surge_warning"],
                surge_reason=row["surge_reason"],
            )
        )
    return result


@router.post("/top5/refresh")
def refresh_global_top5() -> dict:
    """Expand and refresh the market universe without including holdings."""
    job_id = create_analysis_job(
        market="ALL",
        include_recommendations=True,
        include_holdings=False,
    )
    return {
        "success": True,
        "job_id": job_id,
        "message": "보유종목과 무관한 한국·미국 시장 스캔을 시작했습니다.",
    }
