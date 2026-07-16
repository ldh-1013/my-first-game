from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    analytics,
    analyze,
    chat,
    holdings,
    maintenance,
    recommendations,
    reports,
    settings,
    stocks,
)
from app.database import init_db
from app.services.historical_replay_service import recover_historical_replay_runs_on_startup
from app.services.scheduler_service import configure_scheduler, shutdown_scheduler
from app.services.job_manager import recover_analysis_jobs_on_startup


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    recover_analysis_jobs_on_startup()
    recover_historical_replay_runs_on_startup()
    configure_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="Stock Insight AI Assistant",
    version="1.0.0",
    description="무료 데이터 기반 주식 분석·백테스트·포트폴리오 관리 도구",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(holdings.router)
app.include_router(stocks.router)
app.include_router(analyze.router)
app.include_router(chat.router)
app.include_router(reports.router)
app.include_router(recommendations.router)
app.include_router(settings.router)
app.include_router(analytics.router)
app.include_router(maintenance.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Stock Insight AI Assistant",
        "docs": "/docs",
        "notice": "투자 판단을 대신하지 않는 데이터 기반 참고 도구입니다.",
    }
