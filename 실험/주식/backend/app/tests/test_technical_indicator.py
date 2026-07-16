import numpy as np
import pandas as pd

from app.services.technical_indicator import calculate_indicators


def sample_prices(rows: int = 80) -> pd.DataFrame:
    close = np.linspace(100, 130, rows)
    return pd.DataFrame(
        {
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": np.linspace(1000, 3000, rows),
        },
        index=pd.date_range("2025-01-01", periods=rows),
    )


def test_calculates_moving_averages_and_rsi():
    result = calculate_indicators(sample_prices())
    latest = result.iloc[-1]
    assert latest["ma5"] > latest["ma20"] > latest["ma60"]
    assert 0 <= latest["rsi"] <= 100


def test_calculates_volatility_and_volume_change():
    result = calculate_indicators(sample_prices())
    latest = result.iloc[-1]
    assert not pd.isna(latest["volatility_20d"])
    assert not pd.isna(latest["volume_change_rate"])
    assert latest["atr"] > 0

