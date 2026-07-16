SAMPLE_UNIVERSE = [
    {"ticker": "005930.KS", "name": "삼성전자", "market": "KR", "currency": "KRW"},
    {"ticker": "000660.KS", "name": "SK하이닉스", "market": "KR", "currency": "KRW"},
    {"ticker": "035420.KS", "name": "NAVER", "market": "KR", "currency": "KRW"},
    {"ticker": "035720.KS", "name": "카카오", "market": "KR", "currency": "KRW"},
    {"ticker": "207940.KS", "name": "삼성바이오로직스", "market": "KR", "currency": "KRW"},
    {"ticker": "005380.KS", "name": "현대차", "market": "KR", "currency": "KRW"},
    {"ticker": "000270.KS", "name": "기아", "market": "KR", "currency": "KRW"},
    {"ticker": "068270.KS", "name": "셀트리온", "market": "KR", "currency": "KRW"},
    {"ticker": "373220.KS", "name": "LG에너지솔루션", "market": "KR", "currency": "KRW"},
    {"ticker": "105560.KS", "name": "KB금융", "market": "KR", "currency": "KRW"},
    {"ticker": "055550.KS", "name": "신한지주", "market": "KR", "currency": "KRW"},
    {"ticker": "012450.KS", "name": "한화에어로스페이스", "market": "KR", "currency": "KRW"},
    {"ticker": "042660.KS", "name": "한화오션", "market": "KR", "currency": "KRW"},
    {"ticker": "009540.KS", "name": "HD한국조선해양", "market": "KR", "currency": "KRW"},
    {"ticker": "028260.KS", "name": "삼성물산", "market": "KR", "currency": "KRW"},
    {"ticker": "NVDA", "name": "NVIDIA", "market": "US", "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft", "market": "US", "currency": "USD"},
    {"ticker": "AAPL", "name": "Apple", "market": "US", "currency": "USD"},
    {"ticker": "TSLA", "name": "Tesla", "market": "US", "currency": "USD"},
    {"ticker": "AMD", "name": "AMD", "market": "US", "currency": "USD"},
    {"ticker": "GOOGL", "name": "Alphabet", "market": "US", "currency": "USD"},
    {"ticker": "AMZN", "name": "Amazon", "market": "US", "currency": "USD"},
    {"ticker": "META", "name": "Meta", "market": "US", "currency": "USD"},
    {"ticker": "AVGO", "name": "Broadcom", "market": "US", "currency": "USD"},
    {"ticker": "PLTR", "name": "Palantir", "market": "US", "currency": "USD"},
    {"ticker": "SMR", "name": "NuScale Power", "market": "US", "currency": "USD"},
    {"ticker": "NFLX", "name": "Netflix", "market": "US", "currency": "USD"},
    {"ticker": "JPM", "name": "JPMorgan", "market": "US", "currency": "USD"},
    {"ticker": "LLY", "name": "Eli Lilly", "market": "US", "currency": "USD"},
    {"ticker": "COST", "name": "Costco", "market": "US", "currency": "USD"},
]


def select_candidates(report_rows: list[dict], limit: int = 5) -> list[dict]:
    """Surging stocks remain eligible; the UI receives a warning flag instead."""
    return sorted(
        report_rows,
        key=lambda item: (
            item["confidence_level"] != "low",
            _top5_score(
                item["report"].up_probability,
                item["report"].expected_range_high,
            ),
            item["final_score"],
        ),
        reverse=True,
    )[:limit]


def _top5_score(up_probability: float, expected_range_high: float) -> float:
    probability_component = max(0, min(100, up_probability)) * 0.7
    upside_component = max(0, min(20, expected_range_high)) / 20 * 30
    return probability_component + upside_component
