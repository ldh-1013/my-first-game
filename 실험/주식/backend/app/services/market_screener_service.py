from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import requests
import yfinance as yf

from app.utils.logger import get_logger

logger = get_logger(__name__)
_cache: tuple[datetime, list[dict]] | None = None


def discover_market_candidates() -> list[dict]:
    """Discover broad free-market candidates without excluding rapid gainers."""
    global _cache
    now = datetime.now(UTC)
    if _cache and now - _cache[0] < timedelta(minutes=30):
        return list(_cache[1])
    items: dict[str, dict] = {}
    for item in _discover_us()[:30]:
        items[item["ticker"]] = item
    for item in _discover_kr()[:30]:
        items[item["ticker"]] = item
    result = list(items.values())
    _cache = (now, result)
    return result


def _discover_us() -> list[dict]:
    rows: list[dict] = []
    for query in ("day_gainers", "most_actives", "growth_technology_stocks"):
        try:
            payload = yf.screen(query, count=20)
            for quote in payload.get("quotes", []):
                ticker = str(quote.get("symbol") or "").upper()
                if not ticker or any(char in ticker for char in ("^", "=", "/")):
                    continue
                rows.append(
                    {
                        "ticker": ticker,
                        "name": quote.get("shortName") or quote.get("longName") or ticker,
                        "market": "US",
                        "currency": quote.get("currency") or "USD",
                    }
                )
        except Exception as exc:
            logger.warning("US screener %s failed: %s", query, exc)
    return rows


def _discover_kr() -> list[dict]:
    rows: list[dict] = []
    pattern = re.compile(r'code=(\d{6})"[^>]*>([^<]+)</a>')
    headers = {"User-Agent": "Mozilla/5.0 StockInsight/1.0"}
    for market_code, suffix in (("0", ".KS"), ("1", ".KQ")):
        try:
            response = requests.get(
                "https://finance.naver.com/sise/sise_market_sum.naver",
                params={"sosok": market_code, "page": 1},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            text = response.content.decode("euc-kr", errors="ignore")
            for code, name in pattern.findall(text)[:40]:
                rows.append(
                    {
                        "ticker": f"{code}{suffix}",
                        "name": name.strip(),
                        "market": "KR",
                        "currency": "KRW",
                    }
                )
        except Exception as exc:
            logger.warning("KR screener %s failed: %s", market_code, exc)
    return rows
