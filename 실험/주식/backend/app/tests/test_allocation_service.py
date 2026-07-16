from app.services.allocation_service import optimize_allocation


def candidate(ticker: str, price: float, score: float, volatility: float = 30) -> dict:
    return {
        "ticker": ticker,
        "name": ticker,
        "market": "US",
        "currency": "USD",
        "current_price": price,
        "up_probability": 70,
        "expected_2d_return": score,
        "downside_scenario_return": -4,
        "data_quality_score": 90,
        "final_score": 70,
        "annual_volatility": volatility,
        "confidence_level": "medium",
        "surge_warning": False,
        "rsi": 55,
        "returns": {index: index * 0.001 for index in range(20)},
    }


def test_allocation_keeps_cash_and_caps_single_position():
    rows = [candidate(f"S{index}", 10 + index, 5 + index / 10) for index in range(8)]
    result = optimize_allocation(
        rows,
        capital=10_000,
        currency="USD",
        risk_profile="medium",
    )

    assert result["allocations"]
    assert result["cash_reserve"] > 0
    assert result["invested_amount"] <= 8_500
    assert max(row["weight"] for row in result["allocations"]) <= 22.01


def test_low_risk_holds_more_cash_than_high_risk():
    rows = [candidate(f"S{index}", 20, 5 + index / 10) for index in range(10)]
    low = optimize_allocation(
        rows, capital=10_000, currency="USD", risk_profile="low"
    )
    high = optimize_allocation(
        rows, capital=10_000, currency="USD", risk_profile="high"
    )

    assert low["cash_reserve"] > high["cash_reserve"]


def test_low_quality_candidates_are_excluded():
    good = candidate("GOOD", 50, 6)
    poor = candidate("POOR", 50, 12)
    poor["data_quality_score"] = 30
    result = optimize_allocation(
        [good, poor],
        capital=5_000,
        currency="USD",
        risk_profile="medium",
    )

    assert all(row["ticker"] != "POOR" for row in result["allocations"])
