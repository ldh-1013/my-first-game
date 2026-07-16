from typing import Literal

from pydantic import BaseModel, Field


class AllocationRequest(BaseModel):
    capital: float = Field(gt=0)
    currency: Literal["KRW", "USD"] = "KRW"
    risk_profile: Literal["low", "medium", "high"] = "medium"
    max_positions: int | None = Field(default=None, ge=3, le=10)


class AllocationItemRead(BaseModel):
    ticker: str
    name: str
    market: str
    currency: str
    current_price: float
    quantity: int
    amount: float
    weight: float
    up_probability: float
    expected_2d_return: float
    downside_scenario_return: float
    data_quality_score: float
    final_score: float
    annual_volatility: float
    surge_warning: bool
    reason: str


class AllocationPlanRead(BaseModel):
    capital: float
    currency: str
    risk_profile: str
    invested_amount: float
    cash_reserve: float
    cash_reserve_rate: float
    expected_2d_return: float
    expected_profit: float
    downside_scenario_return: float
    downside_scenario_amount: float
    estimated_annual_volatility: float
    allocations: list[AllocationItemRead]
    methodology: list[str]
    warnings: list[str]
    generated_from_reports: int
