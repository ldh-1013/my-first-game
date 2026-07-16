import { ChevronLeft, ChevronRight, Minus, Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { PricePoint } from "../types/stock";

type ValidPoint = PricePoint & {
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
};

export interface PriceLevel {
  label: string;
  value: number;
  tone: "support" | "target" | "resistance" | "forecast";
}

export default function PriceChart({
  data,
  levels = [],
  simple = false,
}: {
  data: PricePoint[];
  levels?: PriceLevel[];
  simple?: boolean;
}) {
  const valid = useMemo(
    () =>
      data.filter(
        (row): row is ValidPoint =>
          row.open_price !== null &&
          row.high_price !== null &&
          row.low_price !== null &&
          row.close_price !== null,
      ),
    [data],
  );
  const [count, setCount] = useState(60);
  const [end, setEnd] = useState(valid.length);
  const [hovered, setHovered] = useState<ValidPoint | null>(null);
  const [indicators, setIndicators] = useState({
    ma5: !simple,
    ma20: true,
    ma60: !simple,
    volume: true,
  });
  useEffect(() => setEnd(valid.length), [valid.length]);
  useEffect(
    () =>
      setIndicators({
        ma5: !simple,
        ma20: true,
        ma60: !simple,
        volume: true,
      }),
    [simple],
  );
  if (!valid.length) return <div className="empty-state chart-empty">가격 데이터가 없습니다.</div>;

  const actualCount = Math.min(count, valid.length);
  const actualEnd = Math.min(end || valid.length, valid.length);
  const visible = valid.slice(Math.max(0, actualEnd - actualCount), actualEnd);
  const width = 1000, priceHeight = 390, volumeHeight = indicators.volume ? 90 : 0;
  const left = 70, top = 25, bottom = 42, gap = indicators.volume ? 35 : 0;
  const totalHeight = top + priceHeight + gap + volumeHeight + bottom;
  const values = visible.flatMap((row) => [
    row.low_price,
    row.high_price,
    ...(indicators.ma5 && row.ma5 !== null ? [row.ma5] : []),
    ...(indicators.ma20 && row.ma20 !== null ? [row.ma20] : []),
    ...(indicators.ma60 && row.ma60 !== null ? [row.ma60] : []),
  ]);
  values.push(...levels.map((level) => level.value));
  const rawMin = Math.min(...values), rawMax = Math.max(...values);
  const padding = Math.max((rawMax - rawMin) * 0.08, rawMax * 0.005);
  const min = rawMin - padding, max = rawMax + padding;
  const plotWidth = width - left - 25;
  const slot = plotWidth / visible.length;
  const candleWidth = Math.max(2, Math.min(13, slot * 0.62));
  const priceY = (value: number) => top + ((max - value) / Math.max(max - min, 0.001)) * priceHeight;
  const maxVolume = Math.max(...visible.map((row) => row.volume ?? 0), 1);
  const volumeTop = top + priceHeight + gap;
  const active = hovered ?? visible[visible.length - 1];
  const xFor = (index: number) => left + slot * index + slot / 2;
  const move = (direction: -1 | 1) =>
    setEnd((current) => Math.min(valid.length, Math.max(actualCount, (current || valid.length) + direction * Math.max(5, Math.floor(actualCount / 4)))));

  return (
    <div className="candle-chart">
      <div className="candle-toolbar">
        <div className="chart-range-buttons">
          {([[20, "1개월"], [60, "3개월"], [120, "6개월"], [valid.length, "전체"]] as const).map(([value, label]) => (
            <button className={actualCount === Math.min(value, valid.length) ? "active" : ""} key={label} onClick={() => { setCount(value); setEnd(valid.length); }}>
              {label}
            </button>
          ))}
        </div>
        {!simple && (
          <>
            <div className="indicator-toggles">
              {(Object.keys(indicators) as Array<keyof typeof indicators>).map((key) => (
                <button className={indicators[key] ? "active" : ""} key={key} onClick={() => setIndicators((current) => ({ ...current, [key]: !current[key] }))}>
                  {key === "volume" ? "거래량" : key.toUpperCase()}
                </button>
              ))}
            </div>
            <div className="chart-controls">
              <button aria-label="과거 구간" onClick={() => move(-1)}><ChevronLeft size={16} /></button>
              <button aria-label="확대" onClick={() => setCount((value) => Math.max(10, value - 10))}><Plus size={16} /></button>
              <button aria-label="축소" onClick={() => setCount((value) => Math.min(valid.length, value + 10))}><Minus size={16} /></button>
              <button aria-label="최신 구간" onClick={() => move(1)}><ChevronRight size={16} /></button>
            </div>
          </>
        )}
      </div>
      {!!levels.length && (
        <div className="price-level-legend">
          {levels.map((level) => (
            <span className={level.tone} key={`${level.label}-${level.value}`}>
              <i />
              {level.label} {formatPrice(level.value)}
            </span>
          ))}
        </div>
      )}
      <div className="candle-summary">
        <strong>{active.date}</strong>
        <span>시 {formatPrice(active.open_price)}</span>
        <span>고 {formatPrice(active.high_price)}</span>
        <span>저 {formatPrice(active.low_price)}</span>
        <span>종 {formatPrice(active.close_price)}</span>
        <span>거래량 {formatVolume(active.volume)}</span>
      </div>
      <div className="candle-svg-wrap">
        <svg viewBox={`0 0 ${width} ${totalHeight}`} role="img" aria-label="일봉 캔들 및 이동평균 차트" onMouseLeave={() => setHovered(null)}>
          {Array.from({ length: 6 }).map((_, index) => {
            const ratio = index / 5, y = top + priceHeight * ratio;
            return <g key={index}><line x1={left} x2={width - 25} y1={y} y2={y} className="chart-grid" /><text x={left - 8} y={y + 4} textAnchor="end" className="chart-axis-label">{formatPrice(max - (max - min) * ratio)}</text></g>;
          })}
          {indicators.ma5 && <path d={linePath(visible, "ma5", xFor, priceY)} className="ma-line ma5" />}
          {indicators.ma20 && <path d={linePath(visible, "ma20", xFor, priceY)} className="ma-line ma20" />}
          {indicators.ma60 && <path d={linePath(visible, "ma60", xFor, priceY)} className="ma-line ma60" />}
          {levels.map((level) => {
            const y = priceY(level.value);
            return (
              <g key={`${level.label}-${level.value}`} className={`price-level ${level.tone}`}>
                <line x1={left} x2={width - 25} y1={y} y2={y} />
                <text x={width - 30} y={y - 5} textAnchor="end">
                  {level.label} {formatPrice(level.value)}
                </text>
              </g>
            );
          })}
          {visible.map((row, index) => {
            const x = xFor(index), up = row.close_price >= row.open_price, color = up ? "#e64b3c" : "#3376d5";
            const openY = priceY(row.open_price), closeY = priceY(row.close_price);
            return <g key={row.date} onMouseEnter={() => setHovered(row)}>
              <rect x={x - slot / 2} y={top} width={slot} height={priceHeight + gap + volumeHeight} fill="transparent" />
              <line x1={x} x2={x} y1={priceY(row.high_price)} y2={priceY(row.low_price)} stroke={color} />
              <rect x={x - candleWidth / 2} y={Math.min(openY, closeY)} width={candleWidth} height={Math.max(1.5, Math.abs(openY - closeY))} fill={up ? color : "#fff"} stroke={color} />
              {indicators.volume && <rect x={x - candleWidth / 2} y={volumeTop + volumeHeight - ((row.volume ?? 0) / maxVolume) * volumeHeight} width={candleWidth} height={((row.volume ?? 0) / maxVolume) * volumeHeight} fill={color} opacity=".45" />}
            </g>;
          })}
          {visible.map((row, index) => {
            const interval = Math.max(1, Math.ceil(visible.length / 7));
            return index % interval === 0 || index === visible.length - 1 ? <text key={`d-${row.date}`} x={xFor(index)} y={totalHeight - 8} textAnchor="middle" className="chart-axis-label">{row.date.slice(5)}</text> : null;
          })}
        </svg>
      </div>
      {valid.length > actualCount && <div className="chart-scroll"><span>과거</span><input type="range" min={actualCount} max={valid.length} value={actualEnd} onChange={(event) => setEnd(Number(event.target.value))} /><span>최신</span></div>}
    </div>
  );
}

function linePath(data: ValidPoint[], key: "ma5" | "ma20" | "ma60", x: (index: number) => number, y: (value: number) => number) {
  let started = false;
  return data.map((row, index) => {
    const value = row[key];
    if (value === null) return "";
    const command = started ? "L" : "M";
    started = true;
    return `${command} ${x(index).toFixed(2)} ${y(value).toFixed(2)}`;
  }).filter(Boolean).join(" ");
}
function formatPrice(value: number | null) { return value === null ? "-" : value.toLocaleString(undefined, { maximumFractionDigits: 2 }); }
function formatVolume(value: number | null) { if (value === null) return "-"; if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`; if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`; if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`; return value.toLocaleString(); }
