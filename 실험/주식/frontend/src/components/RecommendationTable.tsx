import { AlertTriangle, ArrowUpRight } from "lucide-react";

import type { Recommendation } from "../types/recommendation";

export default function RecommendationTable({
  rows,
  onOpen,
  emptyMessage = "분석 결과가 없습니다.",
}: {
  rows: Recommendation[];
  onOpen?: (ticker: string) => void;
  emptyMessage?: string;
}) {
  if (!rows.length) return <div className="empty-state large">{emptyMessage}</div>;
  return (
    <div className="recommendation-list">
      {rows.map((row) => (
        <button key={`${row.ticker}-${row.rank}`} onClick={() => onOpen?.(row.ticker)}>
          <span className="rank">{row.rank}</span>
          <span className="recommendation-name">
            <strong>{row.name}</strong>
            <small>{row.market} · {row.ticker}</small>
          </span>
          {row.surge_warning && (
            <span className="surge-badge" title={row.surge_reason}>
              <AlertTriangle size={14} /> 급등 주의
            </span>
          )}
          <span><small>상승 가능성</small><strong>{row.up_probability.toFixed(1)}%</strong></span>
          <span><small>예상 상단</small><strong>+{row.expected_range_high.toFixed(2)}%</strong></span>
          <ArrowUpRight size={17} />
        </button>
      ))}
    </div>
  );
}
