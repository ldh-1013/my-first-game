from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HoldingCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    market_type: str = Field(default="US", pattern="^(KR|US|PRIVATE|OTHER)$")
    asset_type: str = Field(default="LISTED_STOCK", pattern="^(LISTED_STOCK|PRIVATE|ETF|OTHER)$")
    avg_buy_price: float = Field(default=0, ge=0)
    quantity: float = Field(default=0, ge=0)
    currency: str | None = None
    investment_memo: str | None = None
    interest_level: int = Field(default=3, ge=1, le=5)
    risk_tolerance: str = Field(default="medium", pattern="^(low|medium|high)$")
    tags: list[str] = Field(default_factory=list)


class HoldingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    market_type: str | None = Field(default=None, pattern="^(KR|US|PRIVATE|OTHER)$")
    asset_type: str | None = Field(default=None, pattern="^(LISTED_STOCK|PRIVATE|ETF|OTHER)$")
    avg_buy_price: float | None = Field(default=None, ge=0)
    quantity: float | None = Field(default=None, ge=0)
    currency: str | None = None
    investment_memo: str | None = None
    interest_level: int | None = Field(default=None, ge=1, le=5)
    risk_tolerance: str | None = Field(default=None, pattern="^(low|medium|high)$")
    is_active: bool | None = None
    tags: list[str] | None = None


class HoldingRead(BaseModel):
    id: int
    stock_id: int
    name: str
    ticker: str
    market_type: str
    asset_type: str
    avg_buy_price: float
    quantity: float
    currency: str
    investment_memo: str | None
    interest_level: int
    risk_tolerance: str
    is_active: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
