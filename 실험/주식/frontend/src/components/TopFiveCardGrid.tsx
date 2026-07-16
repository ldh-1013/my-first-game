import { AlertTriangle, ArrowUpRight, BarChart3, TrendingUp } from "lucide-react";
import type { CSSProperties } from "react";

import type { Recommendation } from "../types/recommendation";

export default function TopFiveCardGrid({
  rows,
  onOpen,
  emptyMessage,
}: {
  rows: Recommendation[];
  onOpen: (ticker: string) => void;
  emptyMessage: string;
}) {
  if (!rows.length) return <div className="empty-state large">{emptyMessage}</div>;

  return (
    <div className="top5-card-grid">
      {rows.map((row) => {
        const probability = Math.max(0, Math.min(100, row.up_probability));
        const probabilityStyle = {
          "--probability": `${probability * 3.6}deg`,
        } as CSSProperties;

        return (
          <button
            className={`top5-stock-card rank-${row.rank}`}
            key={`${row.ticker}-${row.rank}`}
            onClick={() => onOpen(row.ticker)}
          >
            <div className="top5-card-header">
              <span className="top5-rank">
                <small>RANK</small>
                <strong>{row.rank}</strong>
              </span>
              <span className="top5-market">{row.market === "KR" ? "한국" : "미국"}</span>
              {row.surge_warning && (
                <span className="top5-surge" title={row.surge_reason}>
                  <AlertTriangle size={14} /> 급등 주의
                </span>
              )}
            </div>

            <div className="top5-card-main">
              <div className="top5-company">
                <span>{row.ticker}</span>
                <h2>{row.name}</h2>
                <p>{row.reason}</p>
              </div>
              <div className="probability-ring" style={probabilityStyle}>
                <div>
                  <small>상승 가능성</small>
                  <strong>{row.up_probability.toFixed(1)}%</strong>
                </div>
              </div>
            </div>

            <div className="top5-metrics">
              <div>
                <TrendingUp size={17} />
                <span>
                  <small>DAY 1 예상 상단</small>
                  <strong>+{row.expected_range_high.toFixed(2)}%</strong>
                </span>
              </div>
              <div>
                <BarChart3 size={17} />
                <span>
                  <small>통합 순위 점수</small>
                  <strong>{row.total_score.toFixed(1)}</strong>
                </span>
              </div>
            </div>

            <div className="top5-range">
              <span>예상 변동 범위</span>
              <div>
                <em>{row.expected_range_low.toFixed(2)}%</em>
                <span>
                  <i style={{ width: `${probability}%` }} />
                </span>
                <strong>+{row.expected_range_high.toFixed(2)}%</strong>
              </div>
            </div>

            <div className="top5-card-footer">
              <span>{row.surge_warning ? row.surge_reason : row.time_horizon}</span>
              <strong>
                상세 분석 보기 <ArrowUpRight size={16} />
              </strong>
            </div>
          </button>
        );
      })}
    </div>
  );
}
