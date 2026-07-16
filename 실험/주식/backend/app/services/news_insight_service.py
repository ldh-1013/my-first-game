from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import DailyReport, NewsArticle, NewsStockLink, SentimentScore, Stock
from app.services.sentiment_analyzer import analyze_sentiment
from app.services.translation_service import translate_many_to_korean


def reprocess_stored_news(
    db: Session,
    stock_id: int | None = None,
    *,
    translate: bool = True,
) -> int:
    statement = select(NewsStockLink)
    if stock_id is not None:
        statement = statement.where(NewsStockLink.stock_id == stock_id)
    links = db.scalars(statement).all()
    articles = {
        article.id: article
        for link in links
        if (article := db.get(NewsArticle, link.article_id)) is not None
    }
    if translate:
        title_articles = [article for article in articles.values() if not article.translated_title]
        translated_titles = translate_many_to_korean(
            [article.title for article in title_articles]
        )
        for article, translated_title in zip(title_articles, translated_titles, strict=False):
            article.translated_title = translated_title

        summary_articles = [
            article
            for article in articles.values()
            if article.summary and not article.translated_summary
        ]
        translated_summaries = translate_many_to_korean(
            [(article.summary or "")[:800] for article in summary_articles]
        )
        for article, translated_summary in zip(
            summary_articles, translated_summaries, strict=False
        ):
            article.translated_summary = translated_summary

    updated = 0
    for link in links:
        article = articles.get(link.article_id)
        if not article:
            continue
        translated_text = f"{article.translated_title or ''} {article.translated_summary or ''}"
        result = analyze_sentiment(article.title, article.summary or "", translated_text)
        sentiment = db.scalar(
            select(SentimentScore).where(
                SentimentScore.article_id == article.id,
                SentimentScore.stock_id == link.stock_id,
            )
        )
        if not sentiment:
            sentiment = SentimentScore(article_id=article.id, stock_id=link.stock_id)
            db.add(sentiment)
        sentiment.sentiment_label = result["sentiment_label"]
        sentiment.sentiment_score = result["sentiment_score"]
        sentiment.short_term_impact = result["short_term_impact"]
        sentiment.long_term_impact = result["long_term_impact"]
        sentiment.confidence = result["confidence"]
        sentiment.model_name = "weighted-news-v3"
        updated += 1
    db.flush()
    affected_stock_ids = {link.stock_id for link in links}
    for affected_stock_id in affected_stock_ids:
        stock = db.get(Stock, affected_stock_id)
        if not stock:
            continue
        insight = build_news_insights(db, affected_stock_id)
        total = (
            insight["positive_count"]
            + insight["negative_count"]
            + insight["neutral_count"]
        )
        summary = (
            f"관련 기사 {total}건 분석 · "
            f"긍정 {insight['positive_count']} · "
            f"부정 {insight['negative_count']} · "
            f"중립 {insight['neutral_count']}"
        )
        reports = db.scalars(
            select(DailyReport).where(DailyReport.stock_id == affected_stock_id)
        ).all()
        for report in reports:
            report.news_summary = summary
    db.commit()
    return updated


def build_news_insights(db: Session, stock_id: int, limit: int = 12) -> dict:
    article_ids = select(NewsStockLink.article_id).where(NewsStockLink.stock_id == stock_id)
    articles = db.scalars(
        select(NewsArticle)
        .where(
            or_(
                NewsArticle.related_stock_id == stock_id,
                NewsArticle.id.in_(article_ids),
            )
        )
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
    ).all()
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    headlines = []
    scores = []
    for article in articles:
        sentiment = db.scalar(
            select(SentimentScore)
            .where(
                SentimentScore.article_id == article.id,
                SentimentScore.stock_id == stock_id,
            )
            .order_by(SentimentScore.created_at.desc())
        )
        label = sentiment.sentiment_label if sentiment else "neutral"
        if label not in counts:
            label = "neutral"
        counts[label] += 1
        if sentiment:
            scores.append(sentiment.sentiment_score)
        headlines.append(
            {
                "title": article.translated_title or article.title,
                "original_title": article.title
                if article.translated_title and article.translated_title != article.title
                else None,
                "source": article.source,
                "sentiment_label": label,
            }
        )
    return {
        "positive_count": counts["positive"],
        "negative_count": counts["negative"],
        "neutral_count": counts["neutral"],
        "sentiment_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "headlines": headlines[:5],
    }
