from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import requests

from app.utils.logger import get_logger
from app.utils.text_cleaner import clean_text

logger = get_logger(__name__)

COMMON_TRANSLATIONS = {
    "stock": "주가",
    "stocks": "주식",
    "shares": "주가",
    "surges": "급등",
    "surge": "급등",
    "jumps": "상승",
    "jump": "상승",
    "rallies": "강세",
    "rally": "강세",
    "rises": "상승",
    "rise": "상승",
    "gains": "상승",
    "gain": "상승",
    "soars": "급등",
    "climbs": "상승",
    "drops": "하락",
    "drop": "하락",
    "falls": "하락",
    "fall": "하락",
    "slides": "약세 지속",
    "slide": "약세",
    "plunges": "급락",
    "declines": "하락",
    "after": "이후",
    "before": "앞두고",
    "earnings": "실적",
    "revenue": "매출",
    "profit": "이익",
    "forecast": "전망",
    "guidance": "실적 전망",
    "upgrade": "상향 평가",
    "downgrade": "하향 평가",
    "target": "목표주가",
    "contract": "계약",
    "deal": "거래",
    "approval": "승인",
    "investigation": "조사",
    "lawsuit": "소송",
    "warning": "경고",
    "record": "사상 최고",
    "investors": "투자자",
    "analysts": "분석가",
}


def contains_korean(value: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in value)


@lru_cache(maxsize=2048)
def translate_to_korean(text: str) -> str:
    value = clean_text(text)
    if not value or contains_korean(value):
        return value
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "ko",
                "dt": "t",
                "q": value[:1800],
            },
            headers={"User-Agent": "Mozilla/5.0 StockInsight/1.0"},
            timeout=4,
        )
        response.raise_for_status()
        payload = response.json()
        translated = "".join(part[0] for part in payload[0] if part and part[0])
        if translated and contains_korean(translated):
            return clean_text(translated)
    except Exception as exc:
        logger.debug("Free translation failed: %s", exc)
    return _fallback_translation(value)


def translate_many_to_korean(values: list[str]) -> list[str]:
    if not values:
        return []
    with ThreadPoolExecutor(max_workers=min(6, len(values))) as executor:
        return list(executor.map(translate_to_korean, values))


def _fallback_translation(text: str) -> str:
    translated = text
    for source, target in sorted(COMMON_TRANSLATIONS.items(), key=lambda row: -len(row[0])):
        translated = re.sub(rf"\b{re.escape(source)}\b", target, translated, flags=re.IGNORECASE)
    return translated
