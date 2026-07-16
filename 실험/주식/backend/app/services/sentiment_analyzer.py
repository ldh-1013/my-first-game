from dataclasses import asdict, dataclass

from app.utils.text_cleaner import clean_text

POSITIVE_WEIGHTS = {
    "beat estimates": 4,
    "beats estimates": 4,
    "earnings beat": 4,
    "record revenue": 4,
    "record profit": 4,
    "raises guidance": 4,
    "guidance raised": 4,
    "contract win": 4,
    "wins contract": 4,
    "target hike": 3,
    "target hikes": 3,
    "price target raised": 3,
    "upgrade": 3,
    "upgraded": 3,
    "approval": 3,
    "approved": 3,
    "partnership": 2,
    "profit growth": 3,
    "revenue growth": 3,
    "strong demand": 2,
    "outperform": 2,
    "bullish": 2,
    "buy rating": 3,
    "surges": 3,
    "surge": 3,
    "soars": 3,
    "jumps": 2,
    "rallies": 2,
    "rally": 2,
    "rises": 2,
    "gains": 2,
    "climbs": 2,
    "record high": 3,
    "수주": 4,
    "흑자 전환": 4,
    "실적 개선": 3,
    "예상 상회": 4,
    "목표주가 상향": 3,
    "계약 체결": 4,
    "공급 계약": 4,
    "승인": 3,
    "사상 최대": 4,
    "매출 증가": 3,
    "영업이익 증가": 3,
    "급등": 3,
    "강세": 2,
    "상승": 2,
}

NEGATIVE_WEIGHTS = {
    "miss estimates": 4,
    "misses estimates": 4,
    "earnings miss": 4,
    "guidance cut": 4,
    "cuts guidance": 4,
    "price target cut": 3,
    "target cut": 3,
    "downgrade": 3,
    "downgraded": 3,
    "investigation": 3,
    "lawsuit": 3,
    "recall": 4,
    "dilution": 4,
    "offering": 2,
    "loss widened": 4,
    "weak demand": 3,
    "underperform": 2,
    "sell rating": 3,
    "overvalued": 2,
    "warning": 2,
    "risk": 1,
    "drops": 3,
    "drop": 3,
    "plunges": 4,
    "tumbles": 4,
    "falls": 3,
    "slides": 3,
    "slide": 3,
    "declines": 2,
    "slump": 3,
    "under water": 3,
    "적자 전환": 4,
    "실적 부진": 3,
    "예상 하회": 4,
    "목표주가 하향": 3,
    "유상증자": 4,
    "소송": 3,
    "조사": 3,
    "리콜": 4,
    "규제": 2,
    "계약 취소": 4,
    "상장폐지": 5,
    "급락": 4,
    "약세": 2,
    "하락": 3,
}


@dataclass
class SentimentResult:
    sentiment_label: str
    sentiment_score: float
    short_term_impact: float
    long_term_impact: float
    confidence: str
    matched_positive: list[str]
    matched_negative: list[str]


def analyze_sentiment(title: str, summary: str = "", translated_text: str = "") -> dict:
    normalized_title = clean_text(title).lower()
    normalized_body = clean_text(f"{summary} {translated_text}").lower()
    positive, positive_score = _matched_score(normalized_title, normalized_body, POSITIVE_WEIGHTS)
    negative, negative_score = _matched_score(normalized_title, normalized_body, NEGATIVE_WEIGHTS)
    net_score = positive_score - negative_score
    score = float(max(-100, min(100, net_score * 9)))

    if net_score >= 2:
        label = "positive"
    elif net_score <= -2:
        label = "negative"
    else:
        label = "neutral"

    total_weight = positive_score + negative_score
    confidence = "high" if total_weight >= 7 else "medium" if total_weight >= 3 else "low"
    return asdict(
        SentimentResult(
            sentiment_label=label,
            sentiment_score=score,
            short_term_impact=round(score * 0.9, 2),
            long_term_impact=round(score * 0.6, 2),
            confidence=confidence,
            matched_positive=positive,
            matched_negative=negative,
        )
    )


def _matched_score(
    title: str,
    body: str,
    weights: dict[str, int],
) -> tuple[list[str], int]:
    matched: list[str] = []
    score = 0
    for phrase, weight in weights.items():
        if phrase in title:
            matched.append(phrase)
            score += weight * 2
        elif phrase in body:
            matched.append(phrase)
            score += weight
    return sorted(set(matched)), score


def aggregate_sentiment(results: list[dict]) -> float:
    if not results:
        return 0.0
    confidence_weight = {"high": 1.0, "medium": 0.8, "low": 0.5}
    weighted = [
        result["sentiment_score"] * confidence_weight.get(result.get("confidence"), 0.5)
        for result in results
    ]
    return round(sum(weighted) / len(weighted), 2)
