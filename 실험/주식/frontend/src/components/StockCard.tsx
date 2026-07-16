import { AlertTriangle, ArrowUpRight, X } from "lucide-react";

import type { DailyReport } from "../types/report";

interface StockCardProps {
  report: DailyReport;
  onOpen: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

function formatPrice(value: number | null) {
  return value === null ? "데이터 없음" : value.toLocaleString("ko-KR");
}

export default function StockCard({ report, onOpen, onRemove }: StockCardProps) {
  const isUp = (report.change_rate ?? 0) >= 0;
  const dayOneUpside =
    report.current_price && report.day1_expected_high
      ? ((report.day1_expected_high / report.current_price - 1) * 100).toFixed(1)
      : null;

  return (
    <article
      className="stock-card stock-card-v2 clickable-card"
      onClick={() => onOpen(report.ticker)}
    >
      <button
        className="stock-card-close"
        type="button"
        title="대시보드에서 숨기기"
        aria-label={`${report.name} 대시보드에서 숨기기`}
        onClick={(event) => {
          event.stopPropagation();
          onRemove(report.ticker);
        }}
      >
        <X size={16} />
      </button>

      {report.surge_warning && (
        <span className="stock-surge-top" title={report.surge_reason}>
          <AlertTriangle size={13} /> 급등 주의
        </span>
      )}

      <header className="stock-card-identity">
        <span>{report.ticker}</span>
        <h3>{report.name}</h3>
      </header>

      <div className="stock-price-v2">
        <strong>{formatPrice(report.current_price)}</strong>
        {report.current_price !== null && (
          <span className={isUp ? "positive" : "negative"}>
            {isUp ? "+" : ""}
            {report.change_rate?.toFixed(2) ?? "0.00"}%
          </span>
        )}
      </div>

      <div className="stock-signal-label">
        <span>상승 가능성</span>
        <strong>{report.up_probability.toFixed(1)}%</strong>
      </div>
      <div className="stock-probability-bar" aria-hidden="true">
        <span style={{ width: `${Math.min(100, Math.max(0, report.up_probability))}%` }} />
      </div>

      <div className="stock-mini-metrics">
        <div>
          <span>DAY 1 상단</span>
          <strong>{dayOneUpside ? `+${dayOneUpside}%` : "-"}</strong>
        </div>
        <div>
          <span>데이터 품질</span>
          <strong>{report.data_quality_score.toFixed(0)}점</strong>
        </div>
      </div>

      <footer className="stock-card-footer-v2">
        <span className={`action-chip ${report.decision_status}`}>{report.action_signal}</span>
        <span className="stock-score-link">
          종합 {report.final_score.toFixed(0)}점 <ArrowUpRight size={15} />
        </span>
      </footer>
    </article>
  );
}
