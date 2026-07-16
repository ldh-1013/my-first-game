import { useEffect, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import NewsList from "../components/NewsList";
import type { Holding } from "../types/holding";
import type { NewsArticle } from "../types/stock";

export default function NewsMonitor() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [ticker, setTicker] = useState("");
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    stockApi.holdings().then((rows) => {
      setHoldings(rows);
      setTicker(rows[0]?.ticker ?? "");
    }).catch((err) => setError(getApiError(err)));
  }, []);
  useEffect(() => {
    if (!ticker) return;
    stockApi.news(ticker).then(setArticles).catch((err) => setError(getApiError(err)));
  }, [ticker]);
  return (
    <div className="page">
      <header className="page-header">
        <div><p className="eyebrow">SOURCE MONITOR</p><h1>뉴스 모니터</h1><p>중복을 제거한 뉴스 원문과 키워드 감성 결과를 확인합니다.</p></div>
        <select className="ticker-select" value={ticker} onChange={(e) => setTicker(e.target.value)}>
          {!holdings.length && <option value="">등록 종목 없음</option>}
          {holdings.map((row) => <option key={row.id} value={row.ticker}>{row.name} · {row.ticker}</option>)}
        </select>
      </header>
      {error && <div className="error-message">{error}</div>}
      <section className="panel"><NewsList articles={articles} /></section>
    </div>
  );
}
