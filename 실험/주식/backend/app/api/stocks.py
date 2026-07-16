import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DailyPrice,
    DailyReport,
    NewsArticle,
    NewsStockLink,
    SentimentScore,
    Stock,
)
from app.schemas.news_schema import NewsRead
from app.schemas.price_schema import IntradayPoint, IntradayResponse, PriceRead
from app.services.price_collector import fetch_intraday_prices

router = APIRouter(prefix="/stocks", tags=["stocks"])


def _stock_or_404(db: Session, ticker: str) -> Stock:
    normalized = ticker.strip().upper()
    stock = db.scalar(select(Stock).where(Stock.ticker == normalized))
    if not stock and normalized.isdigit() and len(normalized) == 6:
        stock = db.scalar(
            select(Stock).where(Stock.ticker.in_([f"{normalized}.KS", f"{normalized}.KQ"]))
        )
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    return stock


@router.get("")
def search_stocks(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(Stock)
    if q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where(or_(Stock.ticker.ilike(pattern), Stock.name.ilike(pattern)))
    rows = db.scalars(statement.order_by(Stock.name).limit(limit)).all()
    return [
        {
            "id": row.id,
            "ticker": row.ticker,
            "name": row.name,
            "market": row.market,
            "tags": json.loads(row.tags or "[]"),
        }
        for row in rows
    ]


@router.get("/{ticker}")
def get_stock(ticker: str, db: Session = Depends(get_db)) -> dict:
    stock = _stock_or_404(db, ticker)
    report = db.scalar(
        select(DailyReport)
        .where(DailyReport.stock_id == stock.id)
        .order_by(DailyReport.report_date.desc())
    )
    return {
        "id": stock.id,
        "name": stock.name,
        "ticker": stock.ticker,
        "market": stock.market,
        "asset_type": stock.asset_type,
        "is_listed": stock.is_listed,
        "currency": stock.currency,
        "tags": json.loads(stock.tags or "[]"),
        "latest_analysis": (
            {
                "report_date": report.report_date,
                "final_score": report.final_score,
                "up_probability": report.up_probability,
                "down_probability": report.down_probability,
                "confidence_level": report.confidence_level,
                "final_view": report.final_view,
                "key_risks": report.key_risks,
                "positive_factors": json.loads(report.positive_factors),
                "negative_factors": json.loads(report.negative_factors),
                "data_quality_score": report.data_quality_score,
                "surge_warning": report.surge_warning,
                "surge_reason": report.surge_reason,
            }
            if report
            else None
        ),
    }


@router.get("/{ticker}/prices", response_model=list[PriceRead])
def get_prices(
    ticker: str,
    limit: int = Query(default=365, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[DailyPrice]:
    stock = _stock_or_404(db, ticker)
    rows = db.scalars(
        select(DailyPrice)
        .where(DailyPrice.stock_id == stock.id)
        .order_by(DailyPrice.date.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


def _calendar_state(stock: Stock) -> tuple[str, str, str]:
    calendar_name = "XKRX" if stock.market == "KR" else "NYSE"
    timezone_name = "Asia/Seoul" if stock.market == "KR" else "America/New_York"
    try:
        import pandas_market_calendars as mcal

        calendar = mcal.get_calendar(calendar_name)
        now = datetime.now(ZoneInfo(timezone_name))
        schedule = calendar.schedule(
            start_date=(now.date() - pd.Timedelta(days=2)),
            end_date=(now.date() + pd.Timedelta(days=2)),
        )
        today = pd.Timestamp(now.date())
        if schedule.empty or today not in schedule.index:
            return "closed", "휴장", timezone_name
        row = schedule.loc[today]
        now_utc = pd.Timestamp(now.astimezone(UTC))
        if row["market_open"] <= now_utc <= row["market_close"]:
            return "open", "장중", timezone_name
        return "closed", "장마감", timezone_name
    except Exception:
        now = datetime.now(ZoneInfo(timezone_name))
        if now.weekday() >= 5:
            return "closed", "휴장", timezone_name
        open_time, close_time = ((9, 0), (15, 30)) if stock.market == "KR" else ((9, 30), (16, 0))
        current = now.hour * 60 + now.minute
        if open_time[0] * 60 + open_time[1] <= current <= close_time[0] * 60 + close_time[1]:
            return "open", "장중", timezone_name
        return "closed", "장마감", timezone_name


@router.get("/{ticker}/intraday", response_model=IntradayResponse)
def get_intraday_prices(
    ticker: str,
    limit: int = Query(default=240, ge=10, le=1000),
    db: Session = Depends(get_db),
) -> IntradayResponse:
    stock = _stock_or_404(db, ticker)
    frame = fetch_intraday_prices(stock.ticker)
    fetched_at = datetime.now(UTC)
    market_state, market_state_label, timezone_name = _calendar_state(stock)
    if frame.empty:
        return IntradayResponse(
            ticker=stock.ticker,
            resolved_ticker=stock.ticker,
            interval="1m",
            refresh_seconds=30,
            fetched_at=fetched_at,
            latest_timestamp=None,
            latest_price=None,
            change_rate=None,
            market_state="no_data",
            market_state_label=f"{market_state_label} · 데이터 없음",
            delay_minutes=None,
            timezone=timezone_name,
            delay_notice="무료 제공처에서 1분봉을 받지 못했습니다. 장 운영 상태와 티커를 확인해 주세요.",
            points=[],
        )
    recent = frame.tail(limit)
    points = [
        IntradayPoint(
            timestamp=index.to_pydatetime(),
            open_price=float(row["open"]),
            high_price=float(row["high"]),
            low_price=float(row["low"]),
            close_price=float(row["close"]),
            volume=float(row["volume"])
            if row.get("volume") is not None and not pd.isna(row.get("volume"))
            else None,
        )
        for index, row in recent.iterrows()
    ]
    latest = points[-1]
    first_close = points[0].close_price
    change_rate = ((latest.close_price / first_close) - 1) * 100 if first_close else None
    latest_utc = (
        latest.timestamp.astimezone(UTC)
        if latest.timestamp.tzinfo
        else latest.timestamp.replace(tzinfo=UTC)
    )
    age_minutes = max(0, (fetched_at - latest_utc).total_seconds() / 60)
    state = "receiving" if market_state == "open" and age_minutes <= 30 else market_state
    label = "수신 중" if state == "receiving" else market_state_label
    return IntradayResponse(
        ticker=stock.ticker,
        resolved_ticker=str(frame.attrs.get("resolved_ticker", stock.ticker)),
        interval="1m",
        refresh_seconds=30,
        fetched_at=fetched_at,
        latest_timestamp=latest.timestamp,
        latest_price=latest.close_price,
        change_rate=round(change_rate, 3) if change_rate is not None else None,
        market_state=state,
        market_state_label=label,
        delay_minutes=round(age_minutes, 1),
        timezone=timezone_name,
        delay_notice=(
            f"무료 1분봉 · 최신 데이터 기준 약 {age_minutes:.0f}분 차이. "
            "실제 체결가보다 15~20분 이상 지연될 수 있습니다."
        ),
        points=points,
    )


@router.get("/{ticker}/news", response_model=list[NewsRead])
def get_news(
    ticker: str,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[NewsRead]:
    stock = _stock_or_404(db, ticker)
    article_ids = select(NewsStockLink.article_id).where(NewsStockLink.stock_id == stock.id)
    articles = db.scalars(
        select(NewsArticle)
        .where(
            or_(
                NewsArticle.related_stock_id == stock.id,
                NewsArticle.id.in_(article_ids),
            )
        )
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
    ).all()
    result = []
    for article in articles:
        sentiment = db.scalar(
            select(SentimentScore)
            .where(
                SentimentScore.article_id == article.id,
                SentimentScore.stock_id == stock.id,
            )
            .order_by(SentimentScore.created_at.desc())
        )
        result.append(
            NewsRead(
                id=article.id,
                title=article.title,
                summary=article.summary,
                translated_title=article.translated_title,
                translated_summary=article.translated_summary,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
                language=article.language,
                is_official=article.is_official,
                is_rumor=article.is_rumor,
                sentiment_label=sentiment.sentiment_label if sentiment else None,
                sentiment_score=sentiment.sentiment_score if sentiment else None,
            )
        )
    return result
