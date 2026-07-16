import { ExternalLink } from "lucide-react";

import type { NewsArticle } from "../types/stock";

const sentimentLabel = {
  positive: "긍정",
  negative: "부정",
  neutral: "중립",
};

function cleanHtml(value: string) {
  return value.replace(/<[^>]+>/g, "").trim();
}

export default function NewsList({ articles }: { articles: NewsArticle[] }) {
  if (!articles.length) return <div className="empty-state">수집된 뉴스가 없습니다.</div>;

  return (
    <div className="news-list news-list-v2">
      {articles.map((article) => {
        const title = article.translated_title || article.title;
        const summary = article.translated_summary || article.summary;
        const label = article.sentiment_label ?? "neutral";
        return (
          <a href={article.url} target="_blank" rel="noreferrer" key={article.id}>
            <div>
              <div className="news-meta">
                <span className={`sentiment-dot ${label}`} />
                <span className={`sentiment ${label}`}>{sentimentLabel[label]}</span>
                <span>
                  {article.source || "출처 미상"} ·{" "}
                  {article.published_at
                    ? new Date(article.published_at).toLocaleString("ko-KR")
                    : "시각 미상"}
                </span>
              </div>
              <h4>{title}</h4>
              {article.translated_title && article.translated_title !== article.title && (
                <small className="news-original-title">{article.title}</small>
              )}
              {summary && <p>{cleanHtml(summary).slice(0, 240)}</p>}
            </div>
            <ExternalLink size={16} />
          </a>
        );
      })}
    </div>
  );
}
