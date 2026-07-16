from pydantic import BaseModel, ConfigDict


class StockRead(BaseModel):
    id: int
    name: str
    ticker: str
    exchange: str | None
    market: str
    country: str | None
    sector: str | None
    industry: str | None
    asset_type: str
    is_listed: bool
    currency: str
    data_source: str

    model_config = ConfigDict(from_attributes=True)

