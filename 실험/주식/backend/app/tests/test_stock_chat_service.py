import json
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (
    DailyPrice,
    DailyReport,
    NewsArticle,
    NewsStockLink,
    SentimentScore,
    Stock,
)
from app.services.stock_chat_service import (
    answer_stock_question,
    build_stock_evidence,
    classify_question,
    resolve_stock,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def seed_stock(db: Session) -> Stock:
    stock = Stock(
        ticker="005930.KS",
        name="삼성전자",
        market="KR",
        country="KR",
        currency="KRW",
        is_listed=True,
    )
    peer = Stock(
        ticker="000660.KS",
        name="SK하이닉스",
        market="KR",
        country="KR",
        currency="KRW",
        is_listed=True,
    )
    db.add_all([stock, peer])
    db.flush()
    start = date(2026, 5, 1)
    for index in range(30):
        current_date = start + timedelta(days=index)
        close = 80000 + index * 100
        if index == 29:
            close = 76000
        db.add(
            DailyPrice(
                stock_id=stock.id,
                date=current_date,
                close_price=close,
                volume=4_000_000 if index == 29 else 1_000_000,
                change_rate=-6 if index == 29 else 0.2,
                ma20=80500,
                rsi=31,
                volatility_20d=38,
            )
        )
        db.add(
            DailyPrice(
                stock_id=peer.id,
                date=current_date,
                close_price=200000 + index * 100,
                volume=500000,
                change_rate=-1 if index == 29 else 0.1,
            )
        )
    report = DailyReport(
        stock_id=stock.id,
        report_date=start + timedelta(days=29),
        current_price=76000,
        change_rate=-6,
        final_score=45,
        up_probability=42,
        down_probability=58,
        data_quality_score=90,
        decision_status="defer",
        negative_factors=json.dumps(["단기 추세 약화"], ensure_ascii=False),
        key_risks="높은 변동성",
    )
    db.add(report)
    article = NewsArticle(
        title="Samsung warns on semiconductor demand",
        translated_title="삼성전자, 반도체 수요 둔화 경고",
        source="Test News",
        url="https://example.com/news",
        published_at=datetime(2026, 5, 29, 8),
        related_stock_id=stock.id,
        content_hash="chat-news-test",
    )
    db.add(article)
    db.flush()
    db.add(NewsStockLink(article_id=article.id, stock_id=stock.id))
    db.add(
        SentimentScore(
            article_id=article.id,
            stock_id=stock.id,
            sentiment_label="negative",
            sentiment_score=-65,
            short_term_impact=-60,
            long_term_impact=-30,
            confidence="high",
        )
    )
    db.commit()
    return stock


def test_korean_stock_name_overrides_page_context_ticker(db):
    samsung = seed_stock(db)
    apple = Stock(
        ticker="AAPL",
        name="Apple",
        market="US",
        country="US",
        currency="USD",
    )
    db.add(apple)
    db.commit()

    resolved = resolve_stock(
        db,
        question="삼성전자는 왜 떨어졌어?",
        ticker="AAPL",
    )

    assert resolved is not None
    assert resolved.id == samsung.id


def test_why_drop_answer_contains_traceable_price_news_and_technical_evidence(db):
    seed_stock(db)

    result = answer_stock_question(
        db,
        question="삼성전자는 왜 떨어졌어? 근거로 분석해줘",
    )

    assert result["stock"]["ticker"] == "005930.KS"
    assert result["question_type"] == "why_move"
    assert result["mode"] == "local_evidence"
    assert "가능성이 높은 설명" in result["answer"]
    assert "news-1" in result["cited_evidence_ids"]
    assert "technical-1" in result["cited_evidence_ids"]
    assert any(row["url"] == "https://example.com/news" for row in result["evidence"])


def test_evidence_calculates_market_relative_move_and_volume_spike(db):
    stock = seed_stock(db)

    package = build_stock_evidence(db, stock)

    assert package["metrics"]["day_return"] < -5
    assert package["metrics"]["volume_ratio"] > 3
    assert package["metrics"]["relative_return"] < 0


def test_unknown_stock_does_not_invent_target(db):
    result = answer_stock_question(
        db,
        question="이 종목 왜 떨어졌어?",
    )

    assert result["stock"] is None
    assert result["question_type"] == "stock_required"
    assert result["confidence"] == "low"


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("왜 떨어졌어?", "why_move"),
        ("관련 뉴스 정리해줘", "news"),
        ("RSI와 거래량 분석", "technical"),
        ("지금 매수해도 돼?", "investment"),
        ("전체 분석해줘", "overview"),
    ],
)
def test_question_classification(question, expected):
    assert classify_question(question) == expected


def test_chat_status_and_validation_endpoint(client):
    status = client.get("/chat/status")
    invalid = client.post("/chat/ask", json={"question": "?"})
    assert status.status_code == 200
    assert status.json()["available"] is True
    assert invalid.status_code == 422
