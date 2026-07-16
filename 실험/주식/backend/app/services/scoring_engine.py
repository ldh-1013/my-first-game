DEFAULT_WEIGHTS = {
    "news": 0.25,
    "technical": 0.20,
    "volume": 0.20,
    "financial": 0.15,
    "industry_macro": 0.15,
    "risk_penalty": 0.05,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def calculate_technical_score(latest: dict | None) -> float:
    if not latest:
        return 0.0

    close = latest.get("close")
    ma5 = latest.get("ma5")
    ma20 = latest.get("ma20")
    ma60 = latest.get("ma60")
    rsi = latest.get("rsi", 50)
    recent_return = latest.get("recent_5d_return", 0) or 0
    if close is None:
        return 0.0

    score = 0.0
    score += 15 if ma5 is not None and close >= ma5 else -15
    score += 15 if ma20 is not None and close >= ma20 else -15
    score += 10 if ma60 is not None and close >= ma60 else -10
    score += clamp(float(recent_return) * 2, -20, 20)
    if rsi is not None:
        if 45 <= rsi <= 65:
            score += 10
        elif rsi >= 75:
            score -= 15
        elif rsi <= 30:
            score -= 5
    return round(clamp(score, -100, 100), 2)


def calculate_volume_score(latest: dict | None) -> float:
    if not latest:
        return 0.0
    volume_change = latest.get("volume_change_rate")
    change_rate = latest.get("change_rate")
    if volume_change is None:
        return 0.0
    direction = 1 if (change_rate or 0) >= 0 else -1
    return round(clamp(float(volume_change) * direction, -100, 100), 2)


def calculate_risk_score(latest: dict | None, has_news: bool, is_listed: bool = True) -> float:
    risk = 0.0
    if not latest:
        risk += 55
    else:
        volatility = latest.get("volatility_20d")
        rsi = latest.get("rsi")
        if volatility is not None:
            risk += clamp((float(volatility) - 20) * 1.2, 0, 45)
        if rsi is not None and (rsi >= 75 or rsi <= 25):
            risk += 15
    if not has_news:
        risk += 15
    if not is_listed:
        risk += 35
    return round(clamp(risk, 0, 100), 2)


def calculate_final_score(
    news_score: float,
    technical_score: float,
    volume_score: float,
    financial_score: float = 0,
    industry_macro_score: float = 0,
    risk_score: float = 0,
    weights: dict[str, float] | None = None,
) -> float:
    selected = weights or DEFAULT_WEIGHTS
    base_score = (
        news_score * selected["news"]
        + technical_score * selected["technical"]
        + volume_score * selected["volume"]
        + financial_score * selected["financial"]
        + industry_macro_score * selected["industry_macro"]
    )
    adjusted_score = base_score - risk_score * selected["risk_penalty"]
    return round(clamp(50 + adjusted_score / 2, 0, 100), 2)

