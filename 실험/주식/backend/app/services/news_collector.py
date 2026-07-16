from urllib.parse import quote_plus

import feedparser
import requests

from app.config import get_settings
from app.services.translation_service import contains_korean, translate_many_to_korean
from app.utils.duplicate_detector import content_hash
from app.utils.logger import get_logger
from app.utils.text_cleaner import clean_text

logger = get_logger(__name__)


def fetch_news_for_ticker(ticker: str, company_name: str) -> list[dict]:
    if not get_settings().enable_external_data:
        return []
    is_korean = ticker.endswith((".KS", ".KQ")) or ticker.split(".")[0].isdigit()
    locale = ("ko", "KR", "KR:ko") if is_korean else ("en-US", "US", "US:en")
    query = quote_plus(f'"{company_name}" OR "{ticker.split(".")[0]}" stock')
    url = (
        f"https://news.google.com/rss/search?q={query}"
        f"&hl={locale[0]}&gl={locale[1]}&ceid={locale[2]}"
    )
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "StockInsightAI/1.0"},
            timeout=get_settings().request_timeout_seconds,
        )
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if getattr(feed, "bozo", False) and not feed.entries:
            return []
        articles, seen_titles = [], set()
        for entry in feed.entries[:20]:
            title = clean_text(entry.get("title"))
            link = entry.get("link", "")
            title_key = title.lower().split(" - ")[0].strip()
            if not title or not link or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            source = entry.get("source", {})
            articles.append(
                {
                    "title": title,
                    "summary": clean_text(entry.get("summary")),
                    "source": source.get("title") if isinstance(source, dict) else str(source),
                    "url": link,
                    "published_at": entry.get("published_parsed"),
                    "content_hash": content_hash(title_key, link),
                }
            )
        articles = articles[:12]
        translation_inputs = [
            f"{row['title']}\n{(row.get('summary') or '')[:500]}"
            if not contains_korean(row["title"])
            else row["title"]
            for row in articles
        ]
        translated = translate_many_to_korean(translation_inputs)
        for article, translated_text in zip(articles, translated):
            if contains_korean(article["title"]):
                article["translated_title"] = article["title"]
                article["translated_summary"] = article.get("summary")
                continue
            parts = translated_text.splitlines()
            article["translated_title"] = clean_text(parts[0]) if parts else article["title"]
            article["translated_summary"] = clean_text(" ".join(parts[1:])) if len(parts) > 1 else None
        return articles
    except Exception as exc:
        logger.warning("News collection failed for %s: %s", ticker, exc)
        return []
