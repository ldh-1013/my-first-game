from datetime import UTC, datetime

import pandas as pd
import yfinance as yf

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
_INTRADAY_CACHE: dict[str, tuple[datetime, pd.DataFrame]] = {}
INTRADAY_CACHE_SECONDS = 15


def ticker_candidates(ticker: str) -> list[str]:
    normalized = ticker.strip().upper()
    if normalized.isdigit() and len(normalized) == 6:
        return [f"{normalized}.KS", f"{normalized}.KQ"]
    return [normalized]


def fetch_daily_prices(ticker: str, period: str = "1y") -> pd.DataFrame:
    if not get_settings().enable_external_data:
        return pd.DataFrame()
    if ticker.upper() in {"SPACEX", "PRIVATE"}:
        logger.info("Price data unavailable for private asset %s", ticker)
        return pd.DataFrame()

    for candidate in ticker_candidates(ticker):
        try:
            frame = yf.Ticker(candidate).history(
                period=period,
                auto_adjust=False,
                timeout=get_settings().request_timeout_seconds,
            )
            if frame.empty:
                logger.warning("No price rows returned for %s", candidate)
                continue
            frame = frame.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Adj Close": "adjusted_close",
                    "Volume": "volume",
                }
            )
            frame.index = pd.to_datetime(frame.index).tz_localize(None)
            frame.attrs["resolved_ticker"] = candidate
            return frame
        except Exception as exc:  # Data providers fail independently from the app.
            logger.warning("Price collection failed for %s: %s", candidate, exc)
    return pd.DataFrame()


def fetch_intraday_prices(
    ticker: str,
    period: str = "1d",
    interval: str = "1m",
) -> pd.DataFrame:
    if not get_settings().enable_external_data:
        return pd.DataFrame()
    if ticker.upper() in {"SPACEX", "PRIVATE"}:
        return pd.DataFrame()

    cache_key = f"{ticker.upper()}:{period}:{interval}"
    cached = _INTRADAY_CACHE.get(cache_key)
    now = datetime.now(UTC)
    if cached and (now - cached[0]).total_seconds() < INTRADAY_CACHE_SECONDS:
        return cached[1].copy()

    for candidate in ticker_candidates(ticker):
        try:
            frame = yf.Ticker(candidate).history(
                period=period,
                interval=interval,
                prepost=True,
                auto_adjust=False,
                timeout=get_settings().request_timeout_seconds,
            )
            if frame.empty:
                logger.warning("No intraday rows returned for %s", candidate)
                continue
            frame = frame.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )
            frame = frame.dropna(subset=["open", "high", "low", "close"])
            frame.attrs["resolved_ticker"] = candidate
            _INTRADAY_CACHE[cache_key] = (now, frame.copy())
            return frame
        except Exception as exc:
            logger.warning("Intraday collection failed for %s: %s", candidate, exc)
    return pd.DataFrame()
