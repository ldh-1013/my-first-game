from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), default="Local User")
    risk_profile: Mapped[str] = mapped_column(String(20), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    ticker: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    exchange: Mapped[str | None] = mapped_column(String(40), nullable=True)
    market: Mapped[str] = mapped_column(String(20), default="US")
    country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(30), default="LISTED_STOCK")
    is_listed: Mapped[bool] = mapped_column(Boolean, default=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    data_source: Mapped[str] = mapped_column(String(50), default="yfinance")
    tags: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    holdings: Mapped[list["Holding"]] = relationship(back_populates="stock")


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    asset_type: Mapped[str] = mapped_column(String(30), default="LISTED_STOCK")
    market_type: Mapped[str] = mapped_column(String(20), default="US")
    avg_buy_price: Mapped[float] = mapped_column(Float, default=0)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    investment_memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    interest_level: Mapped[int] = mapped_column(Integer, default=3)
    risk_tolerance: Mapped[str] = mapped_column(String(20), default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    stock: Mapped[Stock] = relationship(back_populates="holdings")


class DailyPrice(Base):
    __tablename__ = "daily_prices"
    __table_args__ = (UniqueConstraint("stock_id", "date", name="uq_daily_price_stock_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    trading_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma5: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma60: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    atr: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_change_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_title: Mapped[str | None] = mapped_column(String(700), nullable=True)
    translated_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(150), nullable=True)
    url: Mapped[str] = mapped_column(String(1000))
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    related_stock_id: Mapped[int | None] = mapped_column(ForeignKey("stocks.id"), nullable=True)
    related_industry: Mapped[str | None] = mapped_column(String(150), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rumor: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class NewsStockLink(Base):
    __tablename__ = "news_stock_links"
    __table_args__ = (UniqueConstraint("article_id", "stock_id", name="uq_news_stock_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("news_articles.id"), nullable=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    sentiment_label: Mapped[str] = mapped_column(String(20))
    sentiment_score: Mapped[float] = mapped_column(Float)
    short_term_impact: Mapped[float] = mapped_column(Float)
    long_term_impact: Mapped[float] = mapped_column(Float)
    is_price_reflected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    catalyst_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), default="low")
    model_name: Mapped[str] = mapped_column(String(80), default="weighted-news-v3")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    recent_5d_flow: Mapped[str] = mapped_column(String(40), default="data_unavailable")
    volume_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    positive_factors: Mapped[str] = mapped_column(Text, default="[]")
    negative_factors: Mapped[str] = mapped_column(Text, default="[]")
    neutral_factors: Mapped[str] = mapped_column(Text, default="[]")
    news_summary: Mapped[str] = mapped_column(Text, default="")
    technical_analysis: Mapped[str] = mapped_column(Text, default="")
    flow_analysis: Mapped[str] = mapped_column(Text, default="")
    macro_industry_summary: Mapped[str] = mapped_column(Text, default="")
    up_probability: Mapped[float] = mapped_column(Float, default=50)
    down_probability: Mapped[float] = mapped_column(Float, default=50)
    expected_range_low: Mapped[float] = mapped_column(Float, default=0)
    expected_range_high: Mapped[float] = mapped_column(Float, default=0)
    confidence_level: Mapped[str] = mapped_column(String(20), default="low")
    key_risks: Mapped[str] = mapped_column(Text, default="")
    user_checklist: Mapped[str] = mapped_column(Text, default="")
    final_view: Mapped[str] = mapped_column(String(80), default="추가 확인 필요")
    final_score: Mapped[float] = mapped_column(Float, default=50)
    data_quality_score: Mapped[float] = mapped_column(Float, default=0)
    decision_status: Mapped[str] = mapped_column(String(30), default="hold")
    surge_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    surge_reason: Mapped[str] = mapped_column(Text, default="")
    active_model_version: Mapped[str] = mapped_column(
        String(100),
        default="rule-based-v2-calibrated",
    )
    raw_up_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibrated_up_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_sample_count: Mapped[int] = mapped_column(Integer, default=0)
    probability_bucket_observed_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence_basis: Mapped[str] = mapped_column(Text, default="[]")
    market_regime: Mapped[str] = mapped_column(
        String(40),
        default="sideways_low_vol",
    )
    signal_status: Mapped[str] = mapped_column(String(40), default="defer")
    defer_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[float] = mapped_column(Float)
    up_probability: Mapped[float] = mapped_column(Float)
    expected_range_low: Mapped[float] = mapped_column(Float)
    expected_range_high: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    risk_summary: Mapped[str] = mapped_column(Text)
    time_horizon: Mapped[str] = mapped_column(String(50), default="DAY 1~2 관찰")
    checklist: Mapped[str] = mapped_column(Text)
    surge_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    surge_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PredictionResult(Base):
    __tablename__ = "prediction_results"
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "prediction_date",
            "horizon_days",
            "prediction_source",
            "model_version",
            name="uq_prediction_result_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    prediction_date: Mapped[date] = mapped_column(Date)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    final_score: Mapped[float] = mapped_column(Float)
    up_probability: Mapped[float] = mapped_column(Float)
    down_probability: Mapped[float] = mapped_column(Float)
    expected_range_low: Mapped[float] = mapped_column(Float)
    expected_range_high: Mapped[float] = mapped_column(Float)
    confidence_level: Mapped[str] = mapped_column(String(20))
    model_version: Mapped[str] = mapped_column(String(50), default="rule-based-v2")
    horizon_days: Mapped[int] = mapped_column(Integer, default=1)
    prediction_source: Mapped[str] = mapped_column(String(30), default="live", index=True)
    replay_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("historical_replay_runs.id"),
        nullable=True,
        index=True,
    )
    raw_up_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibrated_up_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    range_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actual_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    absolute_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality_note: Mapped[str] = mapped_column(
        String(200),
        default="incomplete",
    )
    historical_news_available: Mapped[bool] = mapped_column(Boolean, default=False)
    historical_financial_available: Mapped[bool] = mapped_column(Boolean, default=False)
    feature_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    market_regime: Mapped[str] = mapped_column(
        String(40),
        default="sideways_low_vol",
    )
    signal_status: Mapped[str] = mapped_column(String(40), default="defer")
    defer_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class HistoricalReplayRun(Base):
    __tablename__ = "historical_replay_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    market_scope: Mapped[str] = mapped_column(String(100), default="KR,US")
    stock_scope: Mapped[str] = mapped_column(String(80), default="current_analysis_universe")
    horizon_days: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    failed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    current_ticker: Mapped[str | None] = mapped_column(String(40), nullable=True)
    current_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    progress_stage: Mapped[str] = mapped_column(String(40), default="queued")
    force_rebuild: Mapped[bool] = mapped_column(Boolean, default=False)
    error_log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ModelExperiment(Base):
    __tablename__ = "model_experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_name: Mapped[str] = mapped_column(String(150), index=True)
    model_type: Mapped[str] = mapped_column(String(80), index=True)
    feature_set_version: Mapped[str] = mapped_column(String(50))
    train_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    train_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    calibration_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    calibration_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    test_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    test_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), default="rejected", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    model_type: Mapped[str] = mapped_column(String(80), index=True)
    artifact_path: Mapped[str] = mapped_column(String(1000), default="")
    metadata_path: Mapped[str] = mapped_column(String(1000), default="")
    feature_schema_json: Mapped[str] = mapped_column(Text, default="[]")
    training_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    validation_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    test_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), default="candidate", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ModelActivationEvent(Base):
    __tablename__ = "model_activation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_version: Mapped[str | None] = mapped_column(String(150), nullable=True)
    to_version: Mapped[str] = mapped_column(String(150))
    action: Mapped[str] = mapped_column(String(40), default="activate")
    reason: Mapped[str] = mapped_column(Text, default="user_confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"
    __table_args__ = (UniqueConstraint("stock_id", "as_of_date", name="uq_financial_stock_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date, index=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_cash_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    trailing_pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_to_book: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_on_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    earnings_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="yfinance")
    raw_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    market: Mapped[str] = mapped_column(String(20), default="ALL")
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    current_ticker: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    error_details: Mapped[str] = mapped_column(Text, default="[]")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int | None] = mapped_column(ForeignKey("stocks.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(30), default="in_app")
    delivery_status: Mapped[str] = mapped_column(String(20), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


__all__ = [
    "User",
    "Stock",
    "Holding",
    "DailyPrice",
    "NewsArticle",
    "NewsStockLink",
    "SentimentScore",
    "DailyReport",
    "Recommendation",
    "PredictionResult",
    "HistoricalReplayRun",
    "ModelExperiment",
    "ModelVersion",
    "FinancialSnapshot",
    "AnalysisJob",
    "AlertEvent",
    "Setting",
]
