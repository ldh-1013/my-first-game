import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"open", "high", "low", "close", "volume"}


def calculate_indicators(price_df: pd.DataFrame) -> pd.DataFrame:
    if price_df.empty:
        return price_df.copy()

    frame = price_df.copy()
    frame.columns = [str(column).lower().replace(" ", "_") for column in frame.columns]
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Missing price columns: {', '.join(sorted(missing))}")

    frame = frame.sort_index()
    close = pd.to_numeric(frame["close"], errors="coerce")
    high = pd.to_numeric(frame["high"], errors="coerce")
    low = pd.to_numeric(frame["low"], errors="coerce")
    volume = pd.to_numeric(frame["volume"], errors="coerce")

    frame["change_rate"] = close.pct_change() * 100
    frame["ma5"] = close.rolling(5, min_periods=1).mean()
    frame["ma20"] = close.rolling(20, min_periods=1).mean()
    frame["ma60"] = close.rolling(60, min_periods=1).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    average_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + relative_strength))
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100)
    rsi = rsi.mask((average_loss == 0) & (average_gain == 0), 50)
    frame["rsi"] = rsi.fillna(50)

    previous_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    frame["atr"] = true_range.rolling(14, min_periods=1).mean()
    frame["volatility_20d"] = close.pct_change().rolling(20, min_periods=5).std() * np.sqrt(252) * 100
    rolling_volume = volume.rolling(20, min_periods=1).mean().replace(0, np.nan)
    frame["volume_change_rate"] = ((volume / rolling_volume) - 1) * 100
    frame["recent_5d_return"] = close.pct_change(5) * 100
    frame["recent_20d_return"] = close.pct_change(20) * 100
    frame["macd"] = close.ewm(span=12, adjust=False).mean() - close.ewm(
        span=26,
        adjust=False,
    ).mean()

    return frame.replace([np.inf, -np.inf], np.nan)
