from __future__ import annotations


def classify_market_regime(
    market_return_20d: float | None,
    market_breadth: float | None,
    market_volatility: float | None,
) -> str:
    """Classify a regime using only information available at the prediction close."""
    trend = float(market_return_20d or 0)
    breadth = float(market_breadth if market_breadth is not None else 0.5)
    volatility = float(market_volatility or 0)
    volatility_label = "high_vol" if volatility >= 45 else "low_vol"
    if trend >= 2 and breadth >= 0.52:
        direction = "bull"
    elif trend <= -2 and breadth <= 0.48:
        direction = "bear"
    else:
        direction = "sideways"
    return f"{direction}_{volatility_label}"


def regime_direction(regime: str) -> str:
    if regime.startswith("bull"):
        return "bull"
    if regime.startswith("bear"):
        return "bear"
    return "sideways"
