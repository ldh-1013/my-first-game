from dataclasses import dataclass

from app.services.price_outlook_service import calculate_price_outlook


@dataclass
class Report:
    current_price: float = 100
    up_probability: float = 70
    expected_range_low: float = -5
    expected_range_high: float = 8
    confidence_level: str = "medium"


@dataclass
class Price:
    close_price: float
    high_price: float
    change_rate: float
    atr: float | None = None
    rsi: float | None = None
    ma20: float | None = None
    ma60: float | None = None


def test_representative_prices_are_inside_forecast_ranges():
    rows = [
        Price(94 + index * 0.3, 95 + index * 0.3, 0.4)
        for index in range(20)
    ]
    result = calculate_price_outlook(Report(), rows)

    assert 95 <= result["day1_expected_price"] <= 108
    assert 93 <= result["day2_expected_price"] <= 111.31
    assert result["day1_expected_price"] > 100


def test_sell_target_reflects_nearby_resistance_and_volatility():
    rows = [
        Price(96, 97, 0.4),
        Price(98, 99, 1.2),
        Price(100, 106, 2.0, atr=3, rsi=62, ma20=97, ma60=93),
        Price(100, 101, 0.1, atr=3, rsi=62, ma20=97, ma60=93),
    ]
    result = calculate_price_outlook(Report(), rows)

    assert 0.8 <= result["sell_target_return"] <= 6
    assert result["sell_target_low"] < result["sell_target_price"] < result["sell_target_high"]
    assert any("저항" in item for item in result["sell_target_basis"])
