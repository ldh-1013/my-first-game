from datetime import date

from pydantic import BaseModel


class RecommendationRead(BaseModel):
    id: int
    report_date: date
    rank: int
    stock_id: int
    ticker: str
    name: str
    market: str
    total_score: float
    up_probability: float
    expected_range_low: float
    expected_range_high: float
    reason: str
    risk_summary: str
    time_horizon: str
    checklist: str
    surge_warning: bool = False
    surge_reason: str = ""
