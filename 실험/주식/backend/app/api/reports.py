import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyReport, Setting, Stock
from app.schemas.report_schema import ReportRead
from app.services.news_insight_service import build_news_insights
from app.services.price_outlook_service import build_price_outlook

router = APIRouter(prefix="/reports", tags=["reports"])
HIDDEN_DASHBOARD_KEY = "hidden_dashboard_tickers"


def _canonical_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    return normalized[:-3] if normalized.endswith((".KS", ".KQ")) else normalized


def _hidden_dashboard_tickers(db: Session) -> set[str]:
    setting = db.scalar(select(Setting).where(Setting.key == HIDDEN_DASHBOARD_KEY))
    if not setting:
        return set()
    try:
        return {_canonical_ticker(str(value)) for value in json.loads(setting.value)}
    except (TypeError, ValueError, json.JSONDecodeError):
        return set()


def _save_hidden_dashboard_tickers(db: Session, values: set[str]) -> None:
    setting = db.scalar(select(Setting).where(Setting.key == HIDDEN_DASHBOARD_KEY))
    encoded = json.dumps(sorted(values), ensure_ascii=False)
    if setting:
        setting.value = encoded
    else:
        db.add(Setting(key=HIDDEN_DASHBOARD_KEY, value=encoded))
    db.commit()


def _price_from_change(current_price: float, change_percent: float) -> float:
    return round(current_price * (1 + change_percent / 100), 2)


def _forecast_fields(db: Session, report: DailyReport) -> dict:
    if report.current_price is None:
        return {
            "day1_expected_low": None,
            "day1_expected_high": None,
            "day1_expected_price": None,
            "day1_expected_return": None,
            "day2_expected_low": None,
            "day2_expected_high": None,
            "day2_expected_price": None,
            "day2_expected_return": None,
            "sell_target_price": None,
            "sell_target_return": None,
            "sell_target_low": None,
            "sell_target_high": None,
            "support_price": None,
            "resistance_price": None,
            "trailing_stop_percent": None,
            "sell_strategy": "가격 데이터가 부족해 매도 목표를 계산하지 못했습니다.",
            "sell_target_basis": [],
            "direction_signal": "가격 데이터 확인 필요",
            "action_signal": "판단 보류",
            "data_status": "unavailable",
        }
    actions = {
        "defer": "판단 보류",
        "buy_watch": "매수 검토",
        "risk_reduce": "매도·위험 축소",
        "hold": "보유·관찰",
    }
    if report.up_probability >= 60:
        direction = "상승 가능성 높음"
    elif report.down_probability >= 60:
        direction = "하락 가능성 높음"
    else:
        direction = "방향성 혼조"
    return {
        "day1_expected_low": _price_from_change(report.current_price, report.expected_range_low),
        "day1_expected_high": _price_from_change(report.current_price, report.expected_range_high),
        "day2_expected_low": _price_from_change(
            report.current_price, report.expected_range_low * 1.4
        ),
        "day2_expected_high": _price_from_change(
            report.current_price, report.expected_range_high * 1.4
        ),
        "direction_signal": direction,
        "action_signal": actions.get(report.decision_status, "보유·관찰"),
        "data_status": "available",
        **build_price_outlook(db, report),
    }


def _serialize(db: Session, report: DailyReport) -> ReportRead:
    stock = db.get(Stock, report.stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="종목 정보를 찾을 수 없습니다.")
    news = build_news_insights(db, report.stock_id)
    return ReportRead(
        id=report.id,
        report_date=report.report_date,
        stock_id=report.stock_id,
        ticker=stock.ticker,
        name=stock.name,
        current_price=report.current_price,
        change_rate=report.change_rate,
        recent_5d_flow=report.recent_5d_flow,
        volume_change=report.volume_change,
        positive_factors=json.loads(report.positive_factors or "[]"),
        negative_factors=json.loads(report.negative_factors or "[]"),
        neutral_factors=json.loads(report.neutral_factors or "[]"),
        news_summary=report.news_summary,
        news_positive_count=news["positive_count"],
        news_negative_count=news["negative_count"],
        news_neutral_count=news["neutral_count"],
        news_sentiment_score=news["sentiment_score"],
        news_headlines=news["headlines"],
        technical_analysis=report.technical_analysis,
        flow_analysis=report.flow_analysis,
        up_probability=report.up_probability,
        down_probability=report.down_probability,
        expected_range_low=report.expected_range_low,
        expected_range_high=report.expected_range_high,
        confidence_level=report.confidence_level,
        key_risks=report.key_risks,
        user_checklist=report.user_checklist,
        final_view=report.final_view,
        final_score=report.final_score,
        data_quality_score=report.data_quality_score,
        decision_status=report.decision_status,
        surge_warning=report.surge_warning,
        surge_reason=report.surge_reason,
        active_model_version=report.active_model_version,
        raw_up_probability=report.raw_up_probability,
        calibrated_up_probability=report.calibrated_up_probability,
        validation_sample_count=report.validation_sample_count,
        probability_bucket_observed_rate=report.probability_bucket_observed_rate,
        confidence_basis=json.loads(report.confidence_basis or "[]"),
        market_regime=report.market_regime,
        signal_status=report.signal_status,
        defer_reason=report.defer_reason,
        **_forecast_fields(db, report),
        created_at=report.created_at,
    )


@router.get("/daily", response_model=list[ReportRead])
def today_reports(db: Session = Depends(get_db)) -> list[ReportRead]:
    hidden = _hidden_dashboard_tickers(db)
    reports = db.scalars(
        select(DailyReport)
        .where(DailyReport.report_date == date.today())
        .order_by(DailyReport.final_score.desc())
    ).all()
    return [
        _serialize(db, report)
        for report in reports
        if (stock := db.get(Stock, report.stock_id))
        and _canonical_ticker(stock.ticker) not in hidden
    ]


@router.get("/dashboard/hidden")
def hidden_dashboard_reports(db: Session = Depends(get_db)) -> list[dict]:
    hidden = _hidden_dashboard_tickers(db)
    stocks = db.scalars(select(Stock).order_by(Stock.name)).all()
    return [
        {"ticker": stock.ticker, "name": stock.name, "market": stock.market}
        for stock in stocks
        if _canonical_ticker(stock.ticker) in hidden
    ]


@router.post("/dashboard/{ticker}/hide")
def hide_dashboard_report(ticker: str, db: Session = Depends(get_db)) -> dict:
    hidden = _hidden_dashboard_tickers(db)
    hidden.add(_canonical_ticker(ticker))
    _save_hidden_dashboard_tickers(db, hidden)
    return {"success": True, "ticker": ticker.strip().upper(), "hidden": True}


@router.delete("/dashboard/{ticker}/hide")
def show_dashboard_report(ticker: str, db: Session = Depends(get_db)) -> dict:
    hidden = _hidden_dashboard_tickers(db)
    hidden.discard(_canonical_ticker(ticker))
    _save_hidden_dashboard_tickers(db, hidden)
    return {"success": True, "ticker": ticker.strip().upper(), "hidden": False}


@router.get("/stock/{ticker}", response_model=ReportRead)
def latest_stock_report(ticker: str, db: Session = Depends(get_db)) -> ReportRead:
    normalized = ticker.strip().upper()
    stock = db.scalar(select(Stock).where(Stock.ticker == normalized))
    if not stock and normalized.isdigit() and len(normalized) == 6:
        stock = db.scalar(
            select(Stock).where(Stock.ticker.in_([f"{normalized}.KS", f"{normalized}.KQ"]))
        )
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    report = db.scalar(
        select(DailyReport)
        .where(DailyReport.stock_id == stock.id)
        .order_by(DailyReport.report_date.desc(), DailyReport.created_at.desc())
    )
    if not report:
        raise HTTPException(status_code=404, detail="아직 생성된 분석 리포트가 없습니다.")
    return _serialize(db, report)


@router.get("/daily/{report_date}", response_model=list[ReportRead])
def reports_by_date(report_date: date, db: Session = Depends(get_db)) -> list[ReportRead]:
    reports = db.scalars(
        select(DailyReport)
        .where(DailyReport.report_date == report_date)
        .order_by(DailyReport.final_score.desc())
    ).all()
    if not reports:
        raise HTTPException(status_code=404, detail="해당 날짜의 리포트가 없습니다.")
    return [_serialize(db, report) for report in reports]
