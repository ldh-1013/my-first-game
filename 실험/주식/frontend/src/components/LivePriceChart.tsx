import { Pause, Play, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import type { IntradayResponse } from "../types/stock";

export default function LivePriceChart({ ticker }: { ticker: string }) {
  const [response, setResponse] = useState<IntradayResponse | null>(null);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState("");
  const [windowSize, setWindowSize] = useState(60);
  const load = useCallback(async () => {
    if (!ticker) return;
    try {
      setResponse(await stockApi.intraday(ticker));
      setError("");
    } catch (err) {
      setError(getApiError(err));
    }
  }, [ticker]);
  useEffect(() => {
    void load();
    if (paused) return;
    const timer = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(timer);
  }, [load, paused]);
  const points = useMemo(() => response?.points.slice(-windowSize) ?? [], [response, windowSize]);
  if (error) return <div className="error-message">{error}</div>;
  if (!response || !points.length) {
    return <div className="empty-state large">1분봉 데이터를 기다리고 있습니다.</div>;
  }
  const width = 1000, height = 340, left = 60, top = 20, bottom = 42;
  const values = points.flatMap((row) => [row.high_price, row.low_price]);
  const min = Math.min(...values), max = Math.max(...values);
  const padding = Math.max((max - min) * 0.08, max * 0.002);
  const low = min - padding, high = max + padding;
  const slot = (width - left - 20) / points.length;
  const y = (value: number) => top + ((high - value) / Math.max(high - low, 0.001)) * (height - top - bottom);
  return (
    <div className="live-chart">
      <div className="chart-toolbar">
        <div>
          <strong>{response.latest_price?.toLocaleString()}</strong>
          <span className={(response.change_rate ?? 0) >= 0 ? "positive" : "negative"}>
            {response.change_rate?.toFixed(2)}%
          </span>
          <span className="market-chip">{response.market_state_label}</span>
        </div>
        <div className="inline-actions">
          {[30, 60, 120, 500].map((value) => (
            <button className={windowSize === value ? "active" : ""} key={value} onClick={() => setWindowSize(value)}>
              {value === 500 ? "전체" : `${value}분`}
            </button>
          ))}
          <button onClick={() => setPaused((value) => !value)}>{paused ? <Play size={15} /> : <Pause size={15} />}</button>
          <button onClick={() => void load()}><RefreshCw size={15} /></button>
        </div>
      </div>
      <div className="chart-scroll">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${ticker} 실시간 캔들 차트`}>
          {points.map((row, index) => {
            const x = left + slot * index + slot / 2;
            const up = row.close_price >= row.open_price;
            const color = up ? "#e64b3c" : "#3376d5";
            const openY = y(row.open_price), closeY = y(row.close_price);
            return (
              <g key={row.timestamp}>
                <line x1={x} x2={x} y1={y(row.high_price)} y2={y(row.low_price)} stroke={color} />
                <rect x={x - Math.max(2, slot * 0.28)} y={Math.min(openY, closeY)} width={Math.max(3, slot * 0.56)} height={Math.max(1.5, Math.abs(openY - closeY))} fill={color} />
              </g>
            );
          })}
        </svg>
      </div>
      <small>{response.delay_notice} · 시간대 {response.timezone}</small>
    </div>
  );
}
