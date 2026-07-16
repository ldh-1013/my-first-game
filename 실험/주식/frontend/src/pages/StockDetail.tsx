import {
  AlertTriangle,
  ChevronDown,
  ExternalLink,
  Maximize2,
  RefreshCw,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import LivePriceChart from "../components/LivePriceChart";
import NewsList from "../components/NewsList";
import PriceChart, { type PriceLevel } from "../components/PriceChart";
import RiskAlert from "../components/RiskAlert";
import type { BacktestSummary } from "../types/analytics";
import type { Holding } from "../types/holding";
import type { DailyReport } from "../types/report";
import type { NewsArticle, PricePoint, StockResearch } from "../types/stock";

type ViewMode = "basic" | "expert";

export default function StockDetail({ initialTicker = "" }: { initialTicker?: string }) {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [report, setReport] = useState<DailyReport | null>(null);
  const [ticker, setTicker] = useState(initialTicker);
  const [prices, setPrices] = useState<PricePoint[]>([]);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [research, setResearch] = useState<StockResearch | null>(null);
  const [backtest, setBacktest] = useState<BacktestSummary | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("basic");
  const chartRef = useRef<HTMLElement>(null);

  useEffect(() => {
    Promise.all([stockApi.holdings(), stockApi.reports()])
      .then(([holdingRows, reportRows]) => {
        setHoldings(holdingRows);
        setReports(reportRows);
        if (!ticker) {
          setTicker(initialTicker || holdingRows[0]?.ticker || reportRows[0]?.ticker || "");
        }
      })
      .catch((err) => setError(getApiError(err)));
  }, [initialTicker]);

  const choices = useMemo(() => {
    const map = new Map<string, { value: string; label: string }>();
    [...reports, ...holdings].forEach((row) =>
      map.set(row.ticker.toUpperCase().replace(/\.(KS|KQ)$/, ""), {
        value: row.ticker,
        label: row.name,
      }),
    );
    if (initialTicker && !map.has(initialTicker)) {
      map.set(initialTicker, { value: initialTicker, label: initialTicker });
    }
    return [...map.values()];
  }, [holdings, reports, initialTicker]);

  const loadStock = async (selected: string, refresh = false) => {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      let [priceRows, newsRows, reportRow] = await Promise.all([
        stockApi.prices(selected),
        stockApi.news(selected),
        stockApi.stockReport(selected),
      ]);
      if (refresh || !priceRows.length || !reportRow) {
        setStatus("최신 가격·뉴스·재무 데이터를 다시 분석하고 있습니다.");
        const result = await stockApi.analyzeTicker(selected);
        [priceRows, newsRows, reportRow] = await Promise.all([
          stockApi.prices(selected),
          stockApi.news(selected),
          stockApi.stockReport(selected),
        ]);
        setStatus(result.message);
      }
      const [researchRow, backtestRow] = await Promise.all([
        stockApi.research(selected).catch(() => null),
        stockApi.backtest(selected).catch(() => null),
      ]);
      setPrices(priceRows);
      setNews(newsRows);
      setReport(reportRow);
      setResearch(researchRow);
      setBacktest(backtestRow);
      if (!priceRows.length) {
        setError("가격 데이터가 없습니다. 종목 코드와 상장 여부를 확인해 주세요.");
      }
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => void loadStock(ticker), [ticker]);

  const latest = prices[prices.length - 1];
  const isUp = report?.direction_signal.includes("상승") ?? false;
  const priceLevels = useMemo<PriceLevel[]>(() => {
    if (!report) return [];
    return [
      report.support_price
        ? { label: "지지", value: report.support_price, tone: "support" as const }
        : null,
      report.resistance_price
        ? { label: "저항", value: report.resistance_price, tone: "resistance" as const }
        : null,
      report.day1_expected_price
        ? { label: "DAY 1", value: report.day1_expected_price, tone: "forecast" as const }
        : null,
      report.day2_expected_price
        ? { label: "DAY 2", value: report.day2_expected_price, tone: "forecast" as const }
        : null,
      report.sell_target_price
        ? { label: "매도 목표", value: report.sell_target_price, tone: "target" as const }
        : null,
    ].filter((value): value is PriceLevel => value !== null);
  }, [report]);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">DEEP DIVE</p>
          <h1>종목 상세 분석</h1>
          <p>기본 화면은 핵심 판단만, 전문가 모드는 모든 근거와 원문을 표시합니다.</p>
        </div>
        <div className="detail-actions">
          <div className="view-mode-toggle" aria-label="분석 화면 모드">
            <button
              className={viewMode === "basic" ? "active" : ""}
              type="button"
              onClick={() => setViewMode("basic")}
            >
              기본
            </button>
            <button
              className={viewMode === "expert" ? "active" : ""}
              type="button"
              onClick={() => setViewMode("expert")}
            >
              전문가
            </button>
          </div>
          <select
            className="ticker-select"
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
          >
            {!choices.length && <option value="">분석 종목 없음</option>}
            {choices.map((row) => (
              <option key={row.value} value={row.value}>
                {row.label} · {row.value}
              </option>
            ))}
          </select>
          <button
            className="ghost-button"
            disabled={!ticker || loading}
            type="button"
            onClick={() => void loadStock(ticker, true)}
          >
            <RefreshCw className={loading ? "spin" : ""} size={16} /> 최신 분석
          </button>
        </div>
      </header>

      {status && <div className="status-message">{status}</div>}
      {error && <div className="error-message">{error}</div>}

      <section className="detail-stats">
        <Stat label="현재가" value={latest?.close_price?.toLocaleString("ko-KR") ?? "-"} />
        <Stat label="일간 변화" value={`${latest?.change_rate?.toFixed(2) ?? "-"}%`} />
        <Stat label="RSI" value={latest?.rsi?.toFixed(1) ?? "-"} />
        <Stat
          label="데이터 품질"
          value={report ? `${report.data_quality_score.toFixed(0)}/100` : "-"}
        />
      </section>

      {report && (
        <>
          {report.surge_warning && (
            <div className="surge-alert">
              <AlertTriangle size={18} />
              <strong>급등 주의</strong>
              <span>{report.surge_reason}</span>
            </div>
          )}

          <section className="core-decision-strip">
            <div>
              <span>핵심 판단</span>
              <strong>{report.direction_signal}</strong>
            </div>
            <div>
              <span>상승 가능성</span>
              <strong>{report.up_probability.toFixed(1)}%</strong>
            </div>
            <div>
              <span>1차 수익 실현</span>
              <strong>{formatSignedPercent(report.sell_target_return)}</strong>
            </div>
            <div>
              <span>핵심 위험</span>
              <strong>{report.surge_warning ? "급등 변동성" : report.final_view}</strong>
            </div>
          </section>

          <section className="prediction-panel">
            <div className="prediction-heading">
              <div>
                <p className="eyebrow">SHORT-TERM OUTLOOK</p>
                <h2>단기 가격 예상</h2>
              </div>
              <div className={`direction-chip ${isUp ? "up" : "down"}`}>
                {isUp ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
                {report.direction_signal}
              </div>
            </div>

            <details className="model-context-card">
              <summary>
                <span>
                  <strong>현재 활성 예측 모델</strong>
                  <small>{report.active_model_version}</small>
                </span>
                <ChevronDown size={16} />
              </summary>
              <div className="model-context-grid">
                <div>
                  <span>원본 상승 확률</span>
                  <strong>
                    {report.raw_up_probability === null
                      ? "-"
                      : `${report.raw_up_probability.toFixed(1)}%`}
                  </strong>
                </div>
                <div>
                  <span>보정 상승 확률</span>
                  <strong>
                    {report.calibrated_up_probability === null
                      ? "-"
                      : `${report.calibrated_up_probability.toFixed(1)}%`}
                  </strong>
                </div>
                <div>
                  <span>검증 참고 표본</span>
                  <strong>{report.validation_sample_count.toLocaleString()}건</strong>
                </div>
                <div>
                  <span>동일 확률 구간 실제 상승</span>
                  <strong>
                    {report.probability_bucket_observed_rate === null
                      ? "-"
                      : `${report.probability_bucket_observed_rate.toFixed(1)}%`}
                  </strong>
                </div>
                <div>
                  <span>시장 국면</span>
                  <strong>{marketRegimeLabel(report.market_regime)}</strong>
                </div>
                <div>
                  <span>선택 신호 상태</span>
                  <strong>
                    {report.signal_status === "high_confidence_signal"
                      ? "고신뢰 신호"
                      : "판단 보류"}
                  </strong>
                </div>
              </div>
              {report.confidence_basis.length > 0 && (
                <ul className="model-confidence-list">
                  {report.confidence_basis.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              )}
            </details>

            <div className="forecast-grid">
              <Forecast
                label="DAY 1 대표 예상가"
                value={formatPrice(report.day1_expected_price, report.ticker)}
                accent={formatSignedPercent(report.day1_expected_return)}
                detail={`가능 범위 ${formatRange(
                  report.day1_expected_low,
                  report.day1_expected_high,
                  report.ticker,
                )}`}
              />
              <Forecast
                label="DAY 2 대표 예상가"
                value={formatPrice(report.day2_expected_price, report.ticker)}
                accent={formatSignedPercent(report.day2_expected_return)}
                detail={`가능 범위 ${formatRange(
                  report.day2_expected_low,
                  report.day2_expected_high,
                  report.ticker,
                )}`}
              />
              <Forecast
                label="상승 / 하락 가능성"
                value={`${report.up_probability.toFixed(1)}% / ${report.down_probability.toFixed(1)}%`}
                detail={`신뢰도 ${confidenceLabel(report.confidence_level)}`}
              />
              <Forecast
                label="매수·매도 참고 신호"
                value={report.action_signal}
                detail={`종합 점수 ${report.final_score.toFixed(1)}`}
              />
            </div>

            <section className="sell-plan-panel">
              <div className="sell-plan-heading">
                <div>
                  <p className="eyebrow">CHART-BASED EXIT PLAN</p>
                  <h3>상승 시 수익 실현 기준</h3>
                </div>
                <span>차트·변동성 통합 분석</span>
              </div>
              <div className="sell-target-grid">
                <div className="sell-target-primary">
                  <span>1차 매도 권장 상승률</span>
                  <strong>{formatSignedPercent(report.sell_target_return)}</strong>
                  <small>목표 구간 진입 시 분할매도 기준</small>
                </div>
                <div>
                  <span>대표 목표가</span>
                  <strong>{formatPrice(report.sell_target_price, report.ticker)}</strong>
                  <small>
                    권장 구간{" "}
                    {formatRange(report.sell_target_low, report.sell_target_high, report.ticker)}
                  </small>
                </div>
                <div>
                  <span>잔여 물량 추적 기준</span>
                  <strong>
                    {report.trailing_stop_percent === null
                      ? "-"
                      : `-${report.trailing_stop_percent.toFixed(1)}%`}
                  </strong>
                  <small>목표가 도달 후 고점 대비 하락 기준</small>
                </div>
              </div>

              <details className="analysis-disclosure" open={viewMode === "expert"}>
                <summary>
                  매도 목표의 계산 근거와 실행 방법
                  <ChevronDown size={16} />
                </summary>
                <div className="sell-analysis-body">
                  <div className="sell-basis-list">
                    {report.sell_target_basis.map((item) => (
                      <p key={item}>
                        <span />
                        {item}
                      </p>
                    ))}
                  </div>
                  <div className="sell-strategy">
                    <strong>추천 실행 방법</strong>
                    <p>{report.sell_strategy}</p>
                  </div>
                </div>
              </details>
              <small className="sell-plan-disclaimer">
                이 목표는 최근 차트에 기반한 참고값이며 실적·공시·시장 급변 시 다시 계산해야 합니다.
              </small>
            </section>
          </section>

          {report.decision_status === "defer" && (
            <RiskAlert>
              {report.defer_reason ||
                "데이터 품질, 검증 표본 또는 예측 확률이 기준에 미달해 현재 판단을 보류합니다."}
            </RiskAlert>
          )}

          <section className="panel compact-news-digest">
            <div className="section-heading">
              <div>
                <p className="eyebrow">INTEGRATED NEWS</p>
                <h2>뉴스 핵심 요약</h2>
              </div>
              <span>
                긍정 {report.news_positive_count} · 부정 {report.news_negative_count} · 중립{" "}
                {report.news_neutral_count}
              </span>
            </div>
            <p>{report.news_summary}</p>
            <div className="compact-headlines">
              {report.news_headlines.slice(0, 3).map((headline) => (
                <div key={headline.title}>
                  <span className={`sentiment-dot ${headline.sentiment_label}`} />
                  <strong>{headline.title}</strong>
                </div>
              ))}
            </div>
            <details className="analysis-disclosure">
              <summary>
                뉴스 영향 요인 펼쳐보기
                <ChevronDown size={16} />
              </summary>
              <div className="factor-grid">
                <div>
                  <span>긍정 요인</span>
                  <p>{report.positive_factors.join(" · ") || "뚜렷한 긍정 신호 없음"}</p>
                </div>
                <div>
                  <span>부정 요인</span>
                  <p>{report.negative_factors.join(" · ") || "뚜렷한 부정 신호 없음"}</p>
                </div>
              </div>
            </details>
          </section>
        </>
      )}

      <section className="panel fullscreen-panel" ref={chartRef}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">PRICE HISTORY</p>
            <h2>{viewMode === "basic" ? "핵심 가격 차트" : "일봉 캔들차트"}</h2>
          </div>
          <button
            className="ghost-button"
            type="button"
            onClick={() => chartRef.current?.requestFullscreen()}
          >
            <Maximize2 size={16} /> 전체화면
          </button>
        </div>
        <PriceChart data={prices} levels={priceLevels} simple={viewMode === "basic"} />
      </section>

      {viewMode === "expert" && (
        <>
          <section className="panel live-price-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">LIVE 1-MINUTE CANDLES</p>
                <h2>준실시간 주가</h2>
              </div>
              <span>무료 제공처 · 지연 가능</span>
            </div>
            <LivePriceChart ticker={ticker} />
          </section>

          <section className="research-grid">
            <article className="panel">
              <div className="section-heading">
                <h2>재무 핵심</h2>
              </div>
              {research?.financial ? (
                <div className="financial-grid">
                  <Stat label="시가총액" value={formatLarge(research.financial.market_cap)} />
                  <Stat label="PER" value={research.financial.trailing_pe?.toFixed(2) ?? "-"} />
                  <Stat label="PBR" value={research.financial.price_to_book?.toFixed(2) ?? "-"} />
                  <Stat label="ROE" value={formatPercent(research.financial.return_on_equity)} />
                  <Stat
                    label="잉여현금흐름"
                    value={formatLarge(research.financial.free_cash_flow)}
                  />
                  <Stat
                    label="이익 성장률"
                    value={formatPercent(research.financial.earnings_growth)}
                  />
                </div>
              ) : (
                <div className="empty-state">수집된 재무 데이터가 없습니다.</div>
              )}
            </article>
            <article className="panel">
              <div className="section-heading">
                <h2>{research?.disclosure_source ?? "공시"} 최근 공시</h2>
              </div>
              <div className="disclosure-list">
                {research?.disclosures.map((row, index) => (
                  <a
                    href={row.url}
                    target="_blank"
                    rel="noreferrer"
                    key={`${row.url}-${index}`}
                  >
                    <span>
                      <strong>{row.title}</strong>
                      <small>
                        {row.date} · {row.source}
                      </small>
                    </span>
                    <ExternalLink size={15} />
                  </a>
                ))}
                {!research?.disclosures.length && (
                  <div className="empty-state">
                    {research?.configuration_required
                      ? "설정에서 무료 DART API 키를 입력해 주세요."
                      : "최근 공시를 가져오지 못했습니다."}
                  </div>
                )}
              </div>
            </article>
          </section>

          <section className="panel">
            <div className="section-heading">
              <h2>이 종목의 예측 검증</h2>
              <span>{backtest?.evaluated ?? 0}건</span>
            </div>
            <p>
              {backtest?.accuracy === null || backtest?.accuracy === undefined
                ? "정산 가능한 과거 예측을 수집 중입니다."
                : `방향 적중률 ${backtest.accuracy.toFixed(1)}% · 평균 예측 오차 ${
                    backtest.mean_absolute_error?.toFixed(2) ?? "-"
                  }%p`}
            </p>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">SOURCE CHECK</p>
                <h2>뉴스 원문</h2>
              </div>
            </div>
            <NewsList articles={news} />
          </section>
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Forecast({
  label,
  value,
  detail,
  accent,
}: {
  label: string;
  value: string;
  detail: string;
  accent?: string;
}) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
      {accent && <em className={accent.startsWith("-") ? "negative" : "positive"}>{accent}</em>}
      <small>{detail}</small>
    </div>
  );
}

function formatRange(low: number | null, high: number | null, ticker: string) {
  return low === null || high === null
    ? "데이터 확인 필요"
    : `${formatPrice(low, ticker)} ~ ${formatPrice(high, ticker)}`;
}

function formatPrice(value: number | null, ticker: string) {
  if (value === null) return "데이터 확인 필요";
  const isKoreanStock = /\.(KS|KQ)$/i.test(ticker);
  return value.toLocaleString("ko-KR", {
    maximumFractionDigits: isKoreanStock ? 0 : 2,
    minimumFractionDigits: isKoreanStock ? 0 : 2,
  });
}

function formatSignedPercent(value: number | null) {
  if (value === null) return "-";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function confidenceLabel(value: string) {
  return value === "high" ? "높음" : value === "medium" ? "중간" : "낮음";
}

function marketRegimeLabel(value: string) {
  const labels: Record<string, string> = {
    bull_low_vol: "상승·저변동",
    bull_high_vol: "상승·고변동",
    bear_low_vol: "하락·저변동",
    bear_high_vol: "하락·고변동",
    sideways_low_vol: "횡보·저변동",
    sideways_high_vol: "횡보·고변동",
  };
  return labels[value] ?? value;
}

function formatLarge(value: number | null) {
  return value === null
    ? "-"
    : new Intl.NumberFormat("ko-KR", {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(value);
}

function formatPercent(value: number | null) {
  return value === null ? "-" : `${(value * 100).toFixed(1)}%`;
}
