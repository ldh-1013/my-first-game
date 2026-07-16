from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PriceRead(BaseModel):
    date: date
    open_price: float | None
    high_price: float | None
    low_price: float | None
    close_price: float | None
    volume: float | None
    change_rate: float | None
    ma5: float | None
    ma20: float | None
    ma60: float | None
    rsi: float | None
    atr: float | None
    volatility_20d: float | None
    volume_change_rate: float | None

    model_config = ConfigDict(from_attributes=True)


class IntradayPoint(BaseModel):
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float | None


class IntradayResponse(BaseModel):
    ticker: str
    resolved_ticker: str
    interval: str
    refresh_seconds: int
    fetched_at: datetime
    latest_timestamp: datetime | None
    latest_price: float | None
    change_rate: float | None
    market_state: str
    market_state_label: str
    delay_minutes: float | None
    timezone: str
    delay_notice: str
    points: list[IntradayPoint]
