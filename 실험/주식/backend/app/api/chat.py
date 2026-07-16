from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.stock_chat_service import answer_stock_question, chat_status

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class StockChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    ticker: str | None = Field(default=None, max_length=40)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=8)


@router.get("/status")
def get_chat_status() -> dict:
    return chat_status()


@router.post("/ask")
def ask_stock_chat(
    payload: StockChatRequest,
    db: Session = Depends(get_db),
) -> dict:
    return answer_stock_question(
        db,
        question=payload.question,
        ticker=payload.ticker,
        history=[row.model_dump() for row in payload.history],
    )
