from datetime import date, datetime

from pydantic import BaseModel


class NewsHeadlineRead(BaseModel):
    title: str
    original_title: str | None = None
    source: str | None = None
    sentiment_label: str


class ReportRead(BaseModel):
    id: int
    report_date: date
    stock_id: int
    ticker: str
    name: str
    current_price: float | None
    change_rate: float | None
    recent_5d_flow: str
    volume_change: float | None
    positive_factors: list[str]
    negative_factors: list[str]
    neutral_factors: list[str]
    news_summary: str
    news_positive_count: int
    news_negative_count: int
    news_neutral_count: int
    news_sentiment_score: float
    news_headlines: list[NewsHeadlineRead]
    technical_analysis: str
    flow_analysis: str
    up_probability: float
    down_probability: float
    expected_range_low: float
    expected_range_high: float
    confidence_level: str
    key_risks: str
    user_checklist: str
    final_view: str
    final_score: float
    day1_expected_low: float | None
    day1_expected_high: float | None
    day1_expected_price: float | None
    day1_expected_return: float | None
    day2_expected_low: float | None
    day2_expected_high: float | None
    day2_expected_price: float | None
    day2_expected_return: float | None
    sell_target_price: float | None
    sell_target_return: float | None
    sell_target_low: float | None
    sell_target_high: float | None
    support_price: float | None
    resistance_price: float | None
    trailing_stop_percent: float | None
    sell_strategy: str
    sell_target_basis: list[str]
    direction_signal: str
    action_signal: str
    data_status: str
    data_quality_score: float
    decision_status: str
    surge_warning: bool
    surge_reason: str
    active_model_version: str
    raw_up_probability: float | None
    calibrated_up_probability: float | None
    validation_sample_count: int
    probability_bucket_observed_rate: float | None
    confidence_basis: list[str]
    market_regime: str
    signal_status: str
    defer_reason: str
    created_at: datetime
