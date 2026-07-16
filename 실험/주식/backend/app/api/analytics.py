from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FinancialSnapshot, HistoricalReplayRun, Stock
from app.schemas.allocation_schema import AllocationPlanRead, AllocationRequest
from app.services.allocation_service import build_allocation_plan
from app.services.alert_service import create_portfolio_alerts, list_alerts
from app.services.backtest_service import backtest_summary
from app.services.historical_replay_service import (
    create_replay_run,
    ensure_daily_validation_run,
    latest_replay_run,
    reconcile_historical_replay_runs,
    serialize_replay_run,
)
from app.services.financial_service import (
    dart_disclosures,
    sec_filings,
    serialize_financial,
)
from app.services.portfolio_service import portfolio_summary
from app.services.performance_diagnostics_service import performance_diagnostics
from app.research.references import research_summary
from app.services.news_insight_service import reprocess_stored_news
from app.services.ml_model_service import (
    activate_model,
    model_detail,
    model_overview,
    restore_baseline_model,
    train_ml_candidates,
)
from app.services.scheduler_service import configure_scheduler, scheduler_status

router = APIRouter(prefix="/analytics", tags=["analytics"])


class HistoricalReplayRequest(BaseModel):
    lookback_years: int = Field(default=2, ge=1, le=5)
    markets: list[str] = Field(default_factory=lambda: ["KR", "US"])
    scope: str = "current_analysis_universe"
    horizon_days: int = Field(default=1, ge=1, le=5)
    force_rebuild: bool = False


class ModelActivationRequest(BaseModel):
    confirmed: bool = False


def _stock(db: Session, ticker: str) -> Stock:
    normalized = ticker.strip().upper()
    stock = db.scalar(select(Stock).where(Stock.ticker == normalized))
    if not stock and normalized.isdigit() and len(normalized) == 6:
        stock = db.scalar(select(Stock).where(Stock.ticker.in_([f"{normalized}.KS", f"{normalized}.KQ"])))
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    return stock


@router.get("/backtest")
def get_backtest(ticker: str | None = None, db: Session = Depends(get_db)) -> dict:
    stock_id = _stock(db, ticker).id if ticker else None
    return backtest_summary(db, stock_id)


def _replay_run(db: Session, run_id: int) -> HistoricalReplayRun:
    run = db.get(HistoricalReplayRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="과거 재현 실행을 찾을 수 없습니다.")
    return run


@router.post("/backtest/replay")
def start_historical_replay(
    payload: HistoricalReplayRequest,
    db: Session = Depends(get_db),
) -> dict:
    markets = [market.upper() for market in payload.markets if market.upper() in {"KR", "US"}]
    if not markets:
        raise HTTPException(status_code=422, detail="KR 또는 US 시장을 하나 이상 선택하세요.")
    run = create_replay_run(
        db,
        lookback_years=payload.lookback_years,
        markets=markets,
        scope=payload.scope,
        horizon_days=payload.horizon_days,
        force_rebuild=payload.force_rebuild,
    )
    return {
        "success": True,
        "run_id": run.id,
        "message": "과거 시점 재현 검증을 백그라운드에서 시작했습니다.",
    }


@router.get("/backtest/replay/latest")
def get_latest_historical_replay(db: Session = Depends(get_db)) -> dict | None:
    reconcile_historical_replay_runs(db)
    run = latest_replay_run(db)
    return serialize_replay_run(run) if run else None


@router.post("/backtest/replay/ensure-daily")
def ensure_daily_historical_replay(db: Session = Depends(get_db)) -> dict:
    run, created, reason = ensure_daily_validation_run(db)
    return {
        "success": True,
        "created": created,
        "reason": reason,
        "run": serialize_replay_run(run),
    }


@router.get("/backtest/replay/{run_id}")
def get_historical_replay(run_id: int, db: Session = Depends(get_db)) -> dict:
    return serialize_replay_run(_replay_run(db, run_id))


@router.get("/backtest/replay/{run_id}/progress")
def get_historical_replay_progress(
    run_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return serialize_replay_run(_replay_run(db, run_id))


@router.get("/backtest/replay/{run_id}/results")
def get_historical_replay_results(
    run_id: int,
    db: Session = Depends(get_db),
) -> dict:
    run = _replay_run(db, run_id)
    return {
        "run": serialize_replay_run(run),
        "summary": backtest_summary(
            db,
            start_date=run.start_date,
            end_date=run.end_date,
            markets=run.market_scope.split(","),
        ),
    }


@router.get("/models")
def get_models(db: Session = Depends(get_db)) -> dict:
    return model_overview(db)


@router.get("/performance/diagnostics")
def get_performance_diagnostics(db: Session = Depends(get_db)) -> dict:
    return performance_diagnostics(db)


@router.get("/research")
def get_research_summary() -> dict:
    return research_summary()


@router.post("/models/train")
def train_models(db: Session = Depends(get_db)) -> dict:
    return train_ml_candidates(db)


@router.post("/models/baseline/activate")
def activate_baseline_model(db: Session = Depends(get_db)) -> dict:
    return restore_baseline_model(db)


@router.get("/models/{model_id}")
def get_model(model_id: int, db: Session = Depends(get_db)) -> dict:
    model = model_detail(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="모델 버전을 찾을 수 없습니다.")
    return model


@router.post("/models/{model_id}/activate")
def activate_candidate_model(
    model_id: int,
    payload: ModelActivationRequest,
    db: Session = Depends(get_db),
) -> dict:
    if not payload.confirmed:
        raise HTTPException(
            status_code=400,
            detail="후보 모델의 한계를 확인한 뒤 다시 적용해 주세요.",
        )
    try:
        return activate_model(db, model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/news/reprocess")
def reprocess_news(ticker: str | None = None, db: Session = Depends(get_db)) -> dict:
    stock_id = _stock(db, ticker).id if ticker else None
    updated = reprocess_stored_news(db, stock_id)
    return {"success": True, "updated": updated}


@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)) -> dict:
    return portfolio_summary(db)


@router.post("/allocation", response_model=AllocationPlanRead)
def create_allocation_plan(
    payload: AllocationRequest,
    db: Session = Depends(get_db),
) -> AllocationPlanRead:
    return AllocationPlanRead(
        **build_allocation_plan(
            db,
            capital=payload.capital,
            currency=payload.currency,
            risk_profile=payload.risk_profile,
            max_positions=payload.max_positions,
        )
    )


@router.get("/stocks/{ticker}/research")
def get_stock_research(ticker: str, db: Session = Depends(get_db)) -> dict:
    stock = _stock(db, ticker)
    financial = db.scalar(
        select(FinancialSnapshot)
        .where(FinancialSnapshot.stock_id == stock.id)
        .order_by(FinancialSnapshot.as_of_date.desc())
    )
    disclosures = dart_disclosures(db, stock) if stock.market == "KR" else sec_filings(stock)
    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "financial": serialize_financial(financial),
        "disclosures": disclosures,
        "disclosure_source": "DART" if stock.market == "KR" else "SEC",
        "configuration_required": stock.market == "KR" and not disclosures,
    }


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)) -> list[dict]:
    return list_alerts(db)


@router.post("/alerts/check")
def check_alerts(db: Session = Depends(get_db)) -> dict:
    events = create_portfolio_alerts(db)
    return {"created": len(events), "alerts": list_alerts(db)}


@router.get("/scheduler")
def get_scheduler() -> dict:
    return scheduler_status()


@router.post("/scheduler/reload")
def reload_scheduler() -> dict:
    return configure_scheduler()
