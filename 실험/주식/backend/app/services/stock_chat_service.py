from __future__ import annotations

import json
import math
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

import numpy as np
import requests
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    DailyPrice,
    DailyReport,
    FinancialSnapshot,
    NewsArticle,
    NewsStockLink,
    SentimentScore,
    Stock,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_EVIDENCE = 14
MAX_HISTORY = 8


def chat_status() -> dict:
    settings = get_settings()
    enhanced = bool(settings.enable_llm_analysis and settings.openai_api_key)
    return {
        "available": True,
        "mode": "openai_grounded" if enhanced else "local_evidence",
        "model": settings.openai_model if enhanced else None,
        "description": (
            "OpenAI 모델이 수집된 근거 안에서만 답변합니다."
            if enhanced
            else "가격·뉴스·기술지표·리포트를 조합한 로컬 근거 엔진입니다."
        ),
    }


def answer_stock_question(
    db: Session,
    *,
    question: str,
    ticker: str | None = None,
    history: list[dict] | None = None,
) -> dict:
    question = question.strip()
    stock = resolve_stock(db, question=question, ticker=ticker)
    if stock is None:
        suggestions = find_stock_suggestions(db, question)
        return {
            "mode": "local_evidence",
            "model": None,
            "stock": None,
            "question_type": "stock_required",
            "headline": "어떤 종목인지 확인이 필요합니다",
            "answer": (
                "질문에 종목명이나 티커를 함께 적어 주세요. "
                "예: “삼성전자는 오늘 왜 떨어졌어?” 또는 “NVDA 뉴스와 차트를 분석해줘.”"
            ),
            "confidence": "low",
            "as_of": None,
            "evidence": [],
            "cited_evidence_ids": [],
            "followups": [
                f"{row['name']}({row['ticker']}) 분석해줘" for row in suggestions[:3]
            ],
            "notice": "종목을 특정하지 않은 상태에서는 임의로 대상을 추정하지 않습니다.",
        }

    package = build_stock_evidence(db, stock)
    question_type = classify_question(question)
    local_answer = build_local_answer(
        stock=stock,
        package=package,
        question=question,
        question_type=question_type,
    )
    settings = get_settings()
    if settings.enable_llm_analysis and settings.openai_api_key:
        try:
            enhanced = generate_openai_answer(
                question=question,
                history=(history or [])[-MAX_HISTORY:],
                stock=stock,
                package=package,
                question_type=question_type,
            )
            if enhanced:
                local_answer.update(enhanced)
                local_answer["mode"] = "openai_grounded"
                local_answer["model"] = settings.openai_model
        except Exception as exc:
            logger.warning("Grounded OpenAI stock chat failed: %s", exc)
            local_answer["notice"] = (
                f"{local_answer['notice']} AI 확장 답변을 불러오지 못해 "
                "로컬 근거 분석으로 답변했습니다."
            )
    return local_answer


def resolve_stock(
    db: Session,
    *,
    question: str,
    ticker: str | None = None,
) -> Stock | None:
    compact_question = _compact(question)
    stocks = db.scalars(select(Stock).order_by(Stock.name)).all()
    direct_matches = []
    for stock in stocks:
        ticker_base = stock.ticker.upper().split(".")[0]
        name_compact = _compact(stock.name)
        if (
            stock.ticker.upper() in question.upper()
            or ticker_base in question.upper().split()
            or (len(name_compact) >= 2 and name_compact in compact_question)
        ):
            direct_matches.append(stock)
    if direct_matches:
        return max(
            direct_matches,
            key=lambda row: max(len(row.name), len(row.ticker)),
        )

    ticker_tokens = re.findall(r"\b[A-Z][A-Z0-9.-]{1,9}\b", question.upper())
    for token in ticker_tokens:
        stock = db.scalar(
            select(Stock).where(
                or_(
                    Stock.ticker == token,
                    Stock.ticker.like(f"{token}.%"),
                )
            )
        )
        if stock:
            return stock
    if ticker:
        normalized = ticker.strip().upper()
        stock = db.scalar(select(Stock).where(Stock.ticker == normalized))
        if not stock and normalized.isdigit() and len(normalized) == 6:
            stock = db.scalar(
                select(Stock).where(
                    Stock.ticker.in_([f"{normalized}.KS", f"{normalized}.KQ"])
                )
            )
        if stock:
            return stock
    return None


def find_stock_suggestions(db: Session, question: str) -> list[dict]:
    compact = _compact(question)
    tokens = [token for token in re.split(r"\s+", compact) if len(token) >= 2]
    rows = db.scalars(select(Stock).order_by(Stock.updated_at.desc()).limit(100)).all()
    scored = []
    for stock in rows:
        target = f"{_compact(stock.name)}{_compact(stock.ticker)}"
        score = sum(1 for token in tokens if token in target)
        if score:
            scored.append((score, stock))
    selected = [row for _score, row in sorted(scored, key=lambda item: -item[0])]
    if not selected:
        selected = rows[:5]
    return [
        {"ticker": row.ticker, "name": row.name, "market": row.market}
        for row in selected[:5]
    ]


def build_stock_evidence(db: Session, stock: Stock) -> dict:
    prices = list(
        db.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_id == stock.id,
                DailyPrice.close_price.is_not(None),
            )
            .order_by(DailyPrice.date.desc())
            .limit(65)
        ).all()
    )
    prices.reverse()
    latest = prices[-1] if prices else None
    previous = prices[-2] if len(prices) >= 2 else None
    close = _number(latest.close_price) if latest else None
    previous_close = _number(previous.close_price) if previous else None
    day_return = (
        (close / previous_close - 1) * 100
        if close is not None and previous_close
        else _number(latest.change_rate) if latest else None
    )
    return_5d = _period_return(prices, 5)
    return_20d = _period_return(prices, 20)
    volume_ratio = _volume_ratio(prices)
    market_return = _market_return(db, stock.market, latest.date if latest else None)
    relative_return = (
        day_return - market_return
        if day_return is not None and market_return is not None
        else None
    )
    report = db.scalar(
        select(DailyReport)
        .where(DailyReport.stock_id == stock.id)
        .order_by(DailyReport.report_date.desc(), DailyReport.created_at.desc())
    )
    financial = db.scalar(
        select(FinancialSnapshot)
        .where(FinancialSnapshot.stock_id == stock.id)
        .order_by(FinancialSnapshot.as_of_date.desc())
    )
    news = _recent_news(db, stock.id)

    evidence: list[dict] = []
    if latest and close is not None:
        evidence.append(
            _evidence(
                "price-1",
                "price",
                f"{latest.date} 종가와 일간 변동",
                (
                    f"종가 {close:,.2f}{stock.currency}, "
                    f"전 거래일 대비 {_signed(day_return)}"
                ),
                "저장된 일봉 가격",
                latest.date,
                strength="fact",
            )
        )
    if return_5d is not None or return_20d is not None:
        evidence.append(
            _evidence(
                "price-2",
                "price",
                "최근 가격 흐름",
                f"5거래일 {_signed(return_5d)}, 20거래일 {_signed(return_20d)}",
                "저장된 일봉 가격 계산",
                latest.date if latest else None,
                strength="fact",
            )
        )
    if market_return is not None:
        evidence.append(
            _evidence(
                "market-1",
                "market",
                f"{stock.market} 분석 유니버스 동향",
                (
                    f"동일 시장 종목 평균 {_signed(market_return)}, "
                    f"종목 상대성과 {_signed(relative_return)}"
                ),
                "동일 시장 저장 종목 평균",
                latest.date if latest else None,
                strength="context",
            )
        )
    if latest:
        technical_parts = [
            f"RSI {_format_number(latest.rsi)}",
            f"20일 변동성 {_format_percent(latest.volatility_20d)}",
            f"20일선 대비 {_ma_gap(close, latest.ma20)}",
            f"거래량 20일 평균 대비 {_format_multiple(volume_ratio)}",
        ]
        evidence.append(
            _evidence(
                "technical-1",
                "technical",
                "기술·거래량 상태",
                ", ".join(technical_parts),
                "저장된 기술지표 계산",
                latest.date,
                strength="context",
            )
        )

    for index, row in enumerate(news[:6], start=1):
        published = row["published_at"] or row["created_at"]
        evidence.append(
            _evidence(
                f"news-{index}",
                "news",
                row["translated_title"] or row["title"],
                (
                    f"감성 {row['sentiment_label'] or '미분류'}"
                    f"({_format_number(row['sentiment_score'])}), "
                    f"출처 {row['source'] or '미상'}"
                ),
                row["source"] or "뉴스 원문",
                published,
                url=row["url"],
                strength="fact" if row["is_official"] else "context",
            )
        )

    if report:
        negative_factors = _json_list(report.negative_factors)
        evidence.append(
            _evidence(
                "report-1",
                "report",
                f"{report.report_date} 종합 분석",
                (
                    f"종합점수 {report.final_score:.1f}, 상승 확률 "
                    f"{report.up_probability:.1f}%, 데이터 품질 "
                    f"{report.data_quality_score:.0f}점, 판단 {report.decision_status}"
                ),
                "Stock Insight 분석 리포트",
                report.report_date,
                strength="context",
            )
        )
        if negative_factors or report.key_risks:
            evidence.append(
                _evidence(
                    "report-2",
                    "report",
                    "리포트의 위험 요인",
                    " · ".join(
                        [*negative_factors[:3], report.key_risks]
                    ).strip(" ·"),
                    "Stock Insight 분석 리포트",
                    report.report_date,
                    strength="hypothesis",
                )
            )
    if financial:
        evidence.append(
            _evidence(
                "financial-1",
                "financial",
                f"{financial.as_of_date} 재무 스냅샷",
                (
                    f"PER {_format_number(financial.trailing_pe)}, "
                    f"PBR {_format_number(financial.price_to_book)}, "
                    f"ROE {_format_ratio_percent(financial.return_on_equity)}, "
                    f"이익성장률 {_format_ratio_percent(financial.earnings_growth)}"
                ),
                financial.source,
                financial.as_of_date,
                strength="context",
            )
        )

    as_of = latest.date if latest else report.report_date if report else None
    metrics = {
        "close": close,
        "day_return": day_return,
        "return_5d": return_5d,
        "return_20d": return_20d,
        "volume_ratio": volume_ratio,
        "rsi": _number(latest.rsi) if latest else None,
        "ma20_gap": _gap(close, _number(latest.ma20) if latest else None),
        "volatility_20d": _number(latest.volatility_20d) if latest else None,
        "market_return": market_return,
        "relative_return": relative_return,
        "up_probability": _number(report.up_probability) if report else None,
        "data_quality_score": _number(report.data_quality_score) if report else None,
    }
    return {
        "as_of": as_of,
        "metrics": metrics,
        "news": news,
        "report": report,
        "financial": financial,
        "evidence": evidence[:MAX_EVIDENCE],
    }


def build_local_answer(
    *,
    stock: Stock,
    package: dict,
    question: str,
    question_type: str,
) -> dict:
    metrics = package["metrics"]
    day_return = metrics["day_return"]
    evidence = package["evidence"]
    causes = _rank_causes(package)
    cited = ["price-1"] if any(row["id"] == "price-1" for row in evidence) else []
    cited.extend(row["evidence_id"] for row in causes)
    cited = list(dict.fromkeys(cited))

    if day_return is None:
        headline = f"{stock.name}의 최신 가격 근거가 부족합니다"
        opening = (
            "저장된 가격 자료가 없어 상승·하락 원인을 수치로 확인할 수 없습니다. "
            "전체 분석을 먼저 실행한 뒤 다시 질문해 주세요."
        )
        confidence = "low"
    else:
        direction = "하락" if day_return < 0 else "상승" if day_return > 0 else "보합"
        headline = f"{stock.name}, 최근 거래일 {_signed(day_return)} {direction}"
        opening = (
            f"확인된 사실은 {package['as_of']} 종가 기준 {_signed(day_return)}입니다. "
        )
        confidence = _answer_confidence(package, causes)

    if question_type == "why_move":
        cause_text = "\n".join(
            f"{index}. {row['text']} [{row['evidence_id']}]"
            for index, row in enumerate(causes[:3], start=1)
        )
        if cause_text:
            answer = (
                f"{opening}\n\n가능성이 높은 설명\n{cause_text}\n\n"
                "중요: 가격 변동의 단일 원인은 거래소 데이터만으로 확정할 수 없습니다. "
                "공식 공시나 회사 발표가 없는 경우 위 내용은 동시 발생한 근거를 바탕으로 한 설명입니다."
            )
        else:
            answer = (
                f"{opening}\n\n저장된 뉴스·시장·기술지표에서는 단일한 악재나 호재가 "
                "확인되지 않았습니다. 수급, 장중 주문 흐름 또는 아직 수집되지 않은 "
                "공시가 영향을 줬을 가능성이 있습니다."
            )
    elif question_type == "news":
        news_rows = [row for row in evidence if row["category"] == "news"][:5]
        cited = [row["id"] for row in news_rows]
        if news_rows:
            answer = "최근 관련 뉴스입니다.\n\n" + "\n".join(
                f"- {row['title']} — {row['detail']} [{row['id']}]"
                for row in news_rows
            )
        else:
            answer = (
                "저장된 최근 관련 뉴스가 없습니다. 뉴스가 없다는 뜻이 아니라, "
                "현재 로컬 데이터베이스에 수집된 근거가 없다는 뜻입니다."
            )
    elif question_type == "technical":
        answer = _technical_answer(stock, package)
        cited = [
            row["id"]
            for row in evidence
            if row["category"] in {"price", "technical", "market"}
        ]
    elif question_type == "investment":
        answer = _investment_answer(stock, package)
        cited = [
            row["id"]
            for row in evidence
            if row["category"] in {"price", "technical", "report", "financial"}
        ]
    else:
        answer = _overview_answer(stock, package, causes)
        cited = [
            row["id"]
            for row in evidence
            if row["category"] in {"price", "technical", "market", "report", "news"}
        ][:8]

    return {
        "mode": "local_evidence",
        "model": None,
        "stock": {
            "ticker": stock.ticker,
            "name": stock.name,
            "market": stock.market,
        },
        "question_type": question_type,
        "headline": headline,
        "answer": answer,
        "confidence": confidence,
        "as_of": package["as_of"],
        "evidence": evidence,
        "cited_evidence_ids": [
            evidence_id
            for evidence_id in cited
            if any(row["id"] == evidence_id for row in evidence)
        ],
        "followups": _followups(stock, question_type),
        "notice": (
            "답변은 저장된 데이터 기준입니다. ‘원인’은 공식 공시로 확인되지 않으면 "
            "확정이 아닌 가능성으로 표현합니다."
        ),
    }


def generate_openai_answer(
    *,
    question: str,
    history: list[dict],
    stock: Stock,
    package: dict,
    question_type: str,
) -> dict | None:
    settings = get_settings()
    allowed_ids = [row["id"] for row in package["evidence"]]
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "headline": {"type": "string"},
            "answer": {"type": "string"},
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "cited_evidence_ids": {
                "type": "array",
                "items": {"type": "string", "enum": allowed_ids or ["none"]},
            },
            "followups": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
        },
        "required": [
            "headline",
            "answer",
            "confidence",
            "cited_evidence_ids",
            "followups",
        ],
    }
    history_text = "\n".join(
        f"{row.get('role', 'user')}: {str(row.get('content', ''))[:1000]}"
        for row in history[-MAX_HISTORY:]
        if row.get("role") in {"user", "assistant"}
    )
    prompt = {
        "question": question,
        "question_type": question_type,
        "stock": {
            "ticker": stock.ticker,
            "name": stock.name,
            "market": stock.market,
        },
        "as_of": str(package["as_of"]) if package["as_of"] else None,
        "metrics": package["metrics"],
        "evidence": package["evidence"],
        "recent_history": history_text,
    }
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "store": False,
            "instructions": (
                "당신은 한국어 주식 리서치 설명 도우미다. 제공된 evidence와 metrics에 "
                "없는 사실을 만들지 않는다. 뉴스와 가격이 동시에 발생했다는 이유만으로 "
                "인과를 확정하지 않는다. 공식 공시가 아닌 설명은 반드시 '가능성'으로 "
                "표현한다. 답변의 핵심 주장 뒤에 [evidence-id]를 붙인다. 매수·매도나 "
                "수익을 보장하지 않는다. 데이터가 부족하면 부족하다고 명확히 말한다."
            ),
            "input": json.dumps(prompt, ensure_ascii=False, default=str),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "grounded_stock_answer",
                    "strict": True,
                    "schema": schema,
                }
            },
        },
        timeout=settings.openai_request_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    output_text = _response_output_text(payload)
    if not output_text:
        return None
    parsed = json.loads(output_text)
    parsed["cited_evidence_ids"] = [
        value for value in parsed["cited_evidence_ids"] if value in allowed_ids
    ]
    return parsed


def classify_question(question: str) -> str:
    compact = _compact(question)
    if any(term in compact for term in ["왜떨어", "왜하락", "왜내려", "왜올라", "왜상승", "이유"]):
        return "why_move"
    if any(term in compact for term in ["뉴스", "기사", "공시", "이슈", "악재", "호재"]):
        return "news"
    if any(term in compact for term in ["차트", "기술적", "지지선", "저항선", "rsi", "거래량"]):
        return "technical"
    if any(term in compact for term in ["매수", "매도", "살까", "팔까", "투자", "목표가"]):
        return "investment"
    return "overview"


def _rank_causes(package: dict) -> list[dict]:
    metrics = package["metrics"]
    day_return = metrics["day_return"]
    falling = day_return is not None and day_return < 0
    causes = []
    for row in package["news"][:8]:
        sentiment = row["sentiment_label"]
        score = abs(_number(row["sentiment_score"]) or 0)
        matches_direction = (falling and sentiment == "negative") or (
            not falling and sentiment == "positive"
        )
        if not matches_direction:
            continue
        evidence_id = next(
            (
                item["id"]
                for item in package["evidence"]
                if item["category"] == "news"
                and item["title"] == (row["translated_title"] or row["title"])
            ),
            None,
        )
        if evidence_id:
            causes.append(
                {
                    "score": 80 + score,
                    "evidence_id": evidence_id,
                    "text": (
                        f"최근 {sentiment == 'negative' and '부정적' or '긍정적'} 뉴스가 "
                        f"가격 방향과 일치합니다: {row['translated_title'] or row['title']}"
                    ),
                }
            )
    market_return = metrics["market_return"]
    relative = metrics["relative_return"]
    if market_return is not None and day_return is not None:
        same_direction = (falling and market_return < -0.3) or (
            not falling and market_return > 0.3
        )
        if same_direction:
            causes.append(
                {
                    "score": 60 + abs(market_return),
                    "evidence_id": "market-1",
                    "text": (
                        f"동일 시장 분석 종목 평균도 {_signed(market_return)}로 "
                        "움직여 시장 전반 영향이 일부 겹쳤습니다."
                    ),
                }
            )
        if relative is not None and abs(relative) >= 1:
            causes.append(
                {
                    "score": 65 + abs(relative),
                    "evidence_id": "market-1",
                    "text": (
                        f"시장 평균 대비 상대성과가 {_signed(relative)}여서 "
                        "종목 고유 요인의 가능성도 남아 있습니다."
                    ),
                }
            )
    ma20_gap = metrics["ma20_gap"]
    volume_ratio = metrics["volume_ratio"]
    rsi = metrics["rsi"]
    if falling and ma20_gap is not None and ma20_gap < -2:
        causes.append(
            {
                "score": 45 + abs(ma20_gap),
                "evidence_id": "technical-1",
                "text": (
                    f"종가가 20일 이동평균보다 {_signed(ma20_gap)} 낮아 "
                    "단기 추세가 약해진 상태입니다."
                ),
            }
        )
    if falling and volume_ratio is not None and volume_ratio >= 1.5:
        causes.append(
            {
                "score": 58 + volume_ratio,
                "evidence_id": "technical-1",
                "text": (
                    f"거래량이 20일 평균의 {volume_ratio:.1f}배로 증가해 "
                    "매도 압력이 평소보다 강했습니다."
                ),
            }
        )
    if falling and rsi is not None and rsi < 35:
        causes.append(
            {
                "score": 42 + (35 - rsi),
                "evidence_id": "technical-1",
                "text": f"RSI {rsi:.1f}로 단기 과매도권에 근접했습니다.",
            }
        )
    if not falling and ma20_gap is not None and ma20_gap > 2:
        causes.append(
            {
                "score": 45 + ma20_gap,
                "evidence_id": "technical-1",
                "text": (
                    f"종가가 20일 이동평균보다 {_signed(ma20_gap)} 높아 "
                    "상승 추세가 유지되고 있습니다."
                ),
            }
        )
    return sorted(causes, key=lambda row: row["score"], reverse=True)


def _technical_answer(stock: Stock, package: dict) -> str:
    metrics = package["metrics"]
    return (
        f"{stock.name}의 {package['as_of']} 기준 기술 상태입니다.\n\n"
        f"- 일간 수익률: {_signed(metrics['day_return'])} [price-1]\n"
        f"- 5거래일 / 20거래일: {_signed(metrics['return_5d'])} / "
        f"{_signed(metrics['return_20d'])} [price-2]\n"
        f"- RSI: {_format_number(metrics['rsi'])}\n"
        f"- 20일선 대비: {_signed(metrics['ma20_gap'])}\n"
        f"- 거래량 비율: {_format_multiple(metrics['volume_ratio'])} [technical-1]\n\n"
        "기술지표는 원인을 설명하기보다 현재 수급과 추세 상태를 보여주는 보조 근거입니다."
    )


def _investment_answer(stock: Stock, package: dict) -> str:
    metrics = package["metrics"]
    report = package["report"]
    if not report:
        return (
            f"{stock.name}의 최신 종합 리포트가 없어 매수·매도 참고 신호를 계산할 수 없습니다. "
            "전체 분석을 먼저 실행해 주세요."
        )
    return (
        f"{stock.name}의 현재 참고 신호는 “{report.decision_status}”입니다 [report-1].\n\n"
        f"- 상승 확률 {report.up_probability:.1f}%, 하락 확률 {report.down_probability:.1f}%\n"
        f"- 데이터 품질 {report.data_quality_score:.0f}점\n"
        f"- 5거래일 흐름 {_signed(metrics['return_5d'])}, 20일선 대비 "
        f"{_signed(metrics['ma20_gap'])} [price-2][technical-1]\n"
        f"- 주요 위험: {report.key_risks or '별도 기록 없음'} [report-2]\n\n"
        "이 수치는 수익을 보장하는 매수·매도 지시가 아닙니다. 진입 여부는 손실 한도와 "
        "공식 공시 확인을 포함해 결정해야 합니다."
    )


def _overview_answer(stock: Stock, package: dict, causes: list[dict]) -> str:
    metrics = package["metrics"]
    report = package["report"]
    cause_line = (
        causes[0]["text"] + f" [{causes[0]['evidence_id']}]"
        if causes
        else "가격 방향을 설명할 뚜렷한 단일 근거는 확인되지 않았습니다."
    )
    report_line = (
        f"종합점수 {report.final_score:.1f}, 상승 확률 {report.up_probability:.1f}%, "
        f"판단 {report.decision_status} [report-1]"
        if report
        else "최신 종합 리포트 없음"
    )
    return (
        f"{stock.name}의 {package['as_of']} 기준 요약입니다.\n\n"
        f"- 가격: 일간 {_signed(metrics['day_return'])}, 5일 {_signed(metrics['return_5d'])}, "
        f"20일 {_signed(metrics['return_20d'])} [price-1][price-2]\n"
        f"- 시장 대비: {_signed(metrics['relative_return'])} [market-1]\n"
        f"- 기술 상태: RSI {_format_number(metrics['rsi'])}, 20일선 대비 "
        f"{_signed(metrics['ma20_gap'])} [technical-1]\n"
        f"- 리포트: {report_line}\n\n"
        f"핵심 해석: {cause_line}"
    )


def _answer_confidence(package: dict, causes: list[dict]) -> str:
    evidence = package["evidence"]
    official_news = any(
        row["category"] == "news" and row["strength"] == "fact"
        for row in evidence
    )
    data_quality = package["metrics"].get("data_quality_score") or 0
    if official_news and causes and data_quality >= 70:
        return "high"
    if causes and data_quality >= 60:
        return "medium"
    return "low"


def _recent_news(db: Session, stock_id: int) -> list[dict]:
    article_ids = select(NewsStockLink.article_id).where(
        NewsStockLink.stock_id == stock_id
    )
    articles = db.scalars(
        select(NewsArticle)
        .where(
            or_(
                NewsArticle.related_stock_id == stock_id,
                NewsArticle.id.in_(article_ids),
            )
        )
        .order_by(
            NewsArticle.published_at.desc(),
            NewsArticle.created_at.desc(),
        )
        .limit(12)
    ).all()
    result = []
    for article in articles:
        sentiment = db.scalar(
            select(SentimentScore)
            .where(
                SentimentScore.article_id == article.id,
                SentimentScore.stock_id == stock_id,
            )
            .order_by(SentimentScore.created_at.desc())
        )
        result.append(
            {
                "title": article.title,
                "translated_title": article.translated_title,
                "source": article.source,
                "url": article.url,
                "published_at": article.published_at,
                "created_at": article.created_at,
                "is_official": article.is_official,
                "is_rumor": article.is_rumor,
                "sentiment_label": (
                    sentiment.sentiment_label if sentiment else None
                ),
                "sentiment_score": (
                    sentiment.sentiment_score if sentiment else None
                ),
            }
        )
    return result


def _market_return(
    db: Session,
    market: str,
    target_date: date | None,
) -> float | None:
    if target_date is None:
        return None
    rows = db.execute(
        select(DailyPrice.close_price, DailyPrice.change_rate)
        .join(Stock, Stock.id == DailyPrice.stock_id)
        .where(
            Stock.market == market,
            DailyPrice.date == target_date,
            DailyPrice.close_price.is_not(None),
        )
    ).all()
    values = [_number(row.change_rate) for row in rows]
    values = [value for value in values if value is not None]
    return float(np.mean(values)) if values else None


def _period_return(prices: list[DailyPrice], sessions: int) -> float | None:
    if len(prices) <= sessions:
        return None
    current = _number(prices[-1].close_price)
    prior = _number(prices[-sessions - 1].close_price)
    if current is None or not prior:
        return None
    return (current / prior - 1) * 100


def _volume_ratio(prices: list[DailyPrice]) -> float | None:
    if not prices:
        return None
    current = _number(prices[-1].volume)
    historical = [
        _number(row.volume) for row in prices[-21:-1] if _number(row.volume)
    ]
    if current is None or not historical:
        return None
    average = float(np.mean(historical))
    return current / average if average else None


def _response_output_text(payload: dict) -> str | None:
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    return payload.get("output_text")


def _followups(stock: Stock, question_type: str) -> list[str]:
    options = {
        "why_move": [
            f"{stock.name} 관련 뉴스를 자세히 정리해줘",
            f"{stock.name} 차트의 지지선과 위험을 알려줘",
            f"{stock.name} 지금 매수 판단은 어때?",
        ],
        "news": [
            f"{stock.name} 가격에 실제로 반영됐는지 분석해줘",
            f"{stock.name} 차트도 함께 분석해줘",
            f"{stock.name} 주요 위험만 정리해줘",
        ],
        "technical": [
            f"{stock.name} 왜 움직였는지 뉴스와 비교해줘",
            f"{stock.name} 매수·매도 참고 신호를 알려줘",
            f"{stock.name} 최근 20일 흐름을 요약해줘",
        ],
    }
    return options.get(
        question_type,
        [
            f"{stock.name} 오늘 왜 움직였어?",
            f"{stock.name} 관련 뉴스 정리해줘",
            f"{stock.name} 차트 분석해줘",
        ],
    )


def _evidence(
    evidence_id: str,
    category: str,
    title: str,
    detail: str,
    source_label: str,
    observed_at: Any,
    *,
    url: str | None = None,
    strength: str = "context",
) -> dict:
    return {
        "id": evidence_id,
        "category": category,
        "title": title,
        "detail": detail,
        "source_label": source_label,
        "url": url,
        "observed_at": observed_at,
        "strength": strength,
    }


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _gap(value: float | None, reference: float | None) -> float | None:
    if value is None or not reference:
        return None
    return (value / reference - 1) * 100


def _ma_gap(value: float | None, reference: float | None) -> str:
    return _signed(_gap(value, _number(reference)))


def _signed(value: float | None) -> str:
    return "-" if value is None else f"{value:+.2f}%"


def _format_percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}%"


def _format_multiple(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}배"


def _format_number(value: Any) -> str:
    number = _number(value)
    return "-" if number is None else f"{number:.2f}"


def _format_ratio_percent(value: Any) -> str:
    number = _number(value)
    return "-" if number is None else f"{number * 100:.1f}%"


def _json_list(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _compact(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", value).lower()
