import { AlertTriangle, ArrowUpRight, Newspaper, TrendingUp } from "lucide-react";

import type { DailyReport } from "../types/report";

const sentimentLabel = {
  positive: "긍정",
  negative: "부정",
  neutral: "중립",
};

export default function ReportCard({ report }: { report: DailyReport }) {
  const totalNews =
    report.news_positive_count + report.news_negative_count + report.news_neutral_count;

  return (
    <article className="report-card daily-report-card">
      <header className="daily-report-head">
        <div>
          <p className="eyebrow">
            {report.report_date} · {report.ticker}
          </p>
          <h3>{report.name}</h3>
        </div>
        <div className="daily-report-head-actions">
          {report.surge_warning && (
            <span className="stock-surge-top static" title={report.surge_reason}>
              <AlertTriangle size={13} /> 급등 주의
            </span>
          )}
          <span className={`action-chip ${report.decision_status}`}>{report.action_signal}</span>
        </div>
      </header>

      <div className="report-key-metrics">
        <div>
          <span>현재가</span>
          <strong>{report.current_price?.toLocaleString("ko-KR") ?? "데이터 없음"}</strong>
          {report.change_rate !== null && (
            <small className={report.change_rate >= 0 ? "positive" : "negative"}>
              {report.change_rate >= 0 ? "+" : ""}
              {report.change_rate.toFixed(2)}%
            </small>
          )}
        </div>
        <div>
          <span>상승 가능성</span>
          <strong>{report.up_probability.toFixed(1)}%</strong>
          <small>{report.direction_signal}</small>
        </div>
        <div>
          <span>종합 점수</span>
          <strong>{report.final_score.toFixed(0)}점</strong>
          <small>데이터 품질 {report.data_quality_score.toFixed(0)}점</small>
        </div>
      </div>

      <section className="report-news-section">
        <div className="report-section-title">
          <span>
            <Newspaper size={17} /> 뉴스 흐름
          </span>
          <small>최근 {totalNews}건 분석</small>
        </div>

        <div className="report-sentiment-row">
          <div className="sentiment-stat positive-tone">
            <span>긍정</span>
            <strong>{report.news_positive_count}</strong>
          </div>
          <div className="sentiment-stat negative-tone">
            <span>부정</span>
            <strong>{report.news_negative_count}</strong>
          </div>
          <div className="sentiment-stat neutral-tone">
            <span>중립</span>
            <strong>{report.news_neutral_count}</strong>
          </div>
        </div>

        <p className="report-news-summary">{report.news_summary}</p>

        {!!report.news_headlines.length && (
          <div className="report-news-list">
            {report.news_headlines.map((headline, index) => (
              <div key={`${headline.title}-${index}`}>
                <span className={`sentiment-dot ${headline.sentiment_label}`} />
                <div>
                  <strong>{headline.title}</strong>
                  <small>
                    {headline.source || "출처 미상"} · {sentimentLabel[headline.sentiment_label]}
                  </small>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="report-analysis-grid">
        <section>
          <span>
            <TrendingUp size={15} /> 기술 흐름
          </span>
          <p>{report.technical_analysis}</p>
        </section>
        <section>
          <span>수급·가격 흐름</span>
          <p>{report.flow_analysis}</p>
        </section>
        <section>
          <span>확인할 위험</span>
          <p>{report.key_risks}</p>
        </section>
      </div>

      <footer className="daily-report-footer">
        <span>{report.final_view}</span>
        <strong>
          상세 분석 보기 <ArrowUpRight size={15} />
        </strong>
      </footer>
    </article>
  );
}
