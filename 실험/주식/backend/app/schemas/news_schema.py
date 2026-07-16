from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewsRead(BaseModel):
    id: int
    title: str
    summary: str | None
    translated_title: str | None = None
    translated_summary: str | None = None
    source: str | None
    url: str
    published_at: datetime | None
    language: str
    is_official: bool
    is_rumor: bool
    sentiment_label: str | None = None
    sentiment_score: float | None = None

    model_config = ConfigDict(from_attributes=True)
