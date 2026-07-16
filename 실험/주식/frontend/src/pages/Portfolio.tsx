import {
  AlertTriangle,
  ArrowUpRight,
  Calculator,
  ChevronDown,
  RefreshCw,
  ShieldCheck,
  WalletCards,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import RiskAlert from "../components/RiskAlert";
import type { AllocationPlan, PortfolioSummary } from "../types/analytics";

type RiskProfile = "low" | "medium" | "high";

const riskLabels: Record<RiskProfile, string> = {
  low: "안정형",
  medium: "균형형",
  high: "공격형",
};

export default function Portfolio({ onOpenStock }: { onOpenStock: (ticker: string) => void }) {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [plan, setPlan] = useState<AllocationPlan | null>(null);
  const [capital, setCapital] = useState(10_000_000);
  const [currency, setCurrency] = useState<"KRW" | "USD">("KRW");
  const [riskProfile, setRiskProfile] = useState<RiskProfile>("medium");
  const [maxPositions, setMaxPositions] = useState(7);
  const [error, setError] = useState("");
  const [loadingPlan, setLoadingPlan] = useState(false);

  const load = () =>
    stockApi
      .portfolio()
      .then(setSummary)
      .catch((err) => setError(getApiError(err)));

  useEffect(() => void load(), []);

  const calculatePlan = () => {
    setError("");
    setLoadingPlan(true);
    stockApi
      .allocation({
          capital,
          currency,
          risk_profile: riskProfile,
          max_positions: maxPositions,
      })
      .then(setPlan)
      .catch((err) => setError(getApiError(err)))
      .finally(() => setLoadingPlan(false));
  };

  const createPlan = (event: FormEvent) => {
    event.preventDefault();
    calculatePlan();
  };

  const changeCurrency = (next: "KRW" | "USD") => {
    setCurrency(next);
    setCapital(next === "KRW" ? 10_000_000 : 10_000);
    setPlan(null);
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">CAPITAL ALLOCATION</p>
          <h1>자산 배분 시뮬레이터</h1>
          <p>
            투자 가능 금액을 입력하면 기대수익과 변동성, 종목 간 상관관계를 함께 고려해
            매수 수량을 계산합니다.
          </p>
        </div>
        <button className="ghost-button" type="button" onClick={load}>
          <RefreshCw size={16} /> 보유 현황 새로고침
        </button>
      </header>

      {error && <div className="error-message">{error}</div>}

      <section className="allocation-builder">
        <form className="allocation-form" onSubmit={createPlan}>
          <div className="allocation-form-title">
            <Calculator size={20} />
            <div>
              <strong>투자 가능 금액 입력</strong>
              <span>현재 보유자산이 아닌, 새로 투자할 수 있는 현금 기준입니다.</span>
            </div>
          </div>

          <label>
            투자 통화
            <div className="currency-toggle">
              <button
                className={currency === "KRW" ? "active" : ""}
                type="button"
                onClick={() => changeCurrency("KRW")}
              >
                원화 · 국내
              </button>
              <button
                className={currency === "USD" ? "active" : ""}
                type="button"
                onClick={() => changeCurrency("USD")}
              >
                달러 · 미국
              </button>
            </div>
          </label>

          <label>
            투자 가능 금액
            <div className="money-input">
              <input
                min={currency === "KRW" ? 100_000 : 100}
                step={currency === "KRW" ? 100_000 : 100}
                type="number"
                value={capital}
                onChange={(event) => setCapital(Number(event.target.value))}
              />
              <span>{currency}</span>
            </div>
          </label>

          <label>
            위험 성향
            <select
              value={riskProfile}
              onChange={(event) => setRiskProfile(event.target.value as RiskProfile)}
            >
              <option value="low">안정형 · 현금 30%</option>
              <option value="medium">균형형 · 현금 15%</option>
              <option value="high">공격형 · 현금 5%</option>
            </select>
          </label>

          <label>
            최대 종목 수
            <select
              value={maxPositions}
              onChange={(event) => setMaxPositions(Number(event.target.value))}
            >
              {[4, 5, 6, 7, 8, 9, 10].map((value) => (
                <option key={value} value={value}>
                  {value}개
                </option>
              ))}
            </select>
          </label>

          <button
            className="primary-button allocation-submit"
            disabled={loadingPlan || capital <= 0}
            type="button"
            onClick={calculatePlan}
          >
            <WalletCards size={17} />
            {loadingPlan ? "최적 비중 계산 중" : "추천 배분 계산"}
          </button>
        </form>

        <aside className="allocation-principles">
          <ShieldCheck size={22} />
          <strong>계산 원칙</strong>
          <p>
            상승 가능성만 높은 종목에 몰지 않고, 데이터 품질·변동성·급등 위험·종목 간
            동조화까지 함께 반영합니다.
          </p>
          <span>수익 보장이 아닌 위험 조정 시뮬레이션</span>
        </aside>
      </section>

      {plan && (
        <section className="allocation-result">
          <div className="allocation-result-head">
            <div>
              <p className="eyebrow">SIMULATED PLAN</p>
              <h2>{riskLabels[plan.risk_profile]} 추천 배분</h2>
            </div>
            <span>최신 리포트 {plan.generated_from_reports}개 비교</span>
          </div>

          <div className="allocation-summary-grid">
            <AllocationMetric
              label="실제 매수 예정액"
              value={formatMoney(plan.invested_amount, plan.currency)}
              detail={`현금 ${plan.cash_reserve_rate.toFixed(1)}% 유지`}
            />
            <AllocationMetric
              label="DAY 2 기준 기대수익"
              value={formatSigned(plan.expected_2d_return, "%")}
              detail={formatSignedMoney(plan.expected_profit, plan.currency)}
              tone="positive"
            />
            <AllocationMetric
              label="하락 시나리오"
              value={formatSigned(plan.downside_scenario_return, "%")}
              detail={formatSignedMoney(plan.downside_scenario_amount, plan.currency)}
              tone="negative"
            />
            <AllocationMetric
              label="추정 연 변동성"
              value={`${plan.estimated_annual_volatility.toFixed(1)}%`}
              detail="낮을수록 가격 흔들림이 작음"
            />
          </div>

          {plan.allocations.length ? (
            <div className="allocation-table">
              <div className="allocation-row allocation-header">
                <span>종목</span>
                <span>추천 수량</span>
                <span>투자 금액</span>
                <span>비중</span>
                <span>기대수익</span>
                <span />
              </div>
              {plan.allocations.map((row, index) => (
                <button
                  className="allocation-row"
                  type="button"
                  key={row.ticker}
                  onClick={() => onOpenStock(row.ticker)}
                >
                  <span className="allocation-stock">
                    <i>{index + 1}</i>
                    <span>
                      <strong>{row.name}</strong>
                      <small>
                        {row.ticker}
                        {row.surge_warning ? " · 급등 주의" : ""}
                      </small>
                    </span>
                  </span>
                  <strong>{row.quantity.toLocaleString("ko-KR")}주</strong>
                  <span>{formatMoney(row.amount, row.currency)}</span>
                  <span>{row.weight.toFixed(1)}%</span>
                  <span className={row.expected_2d_return >= 0 ? "positive" : "negative"}>
                    {formatSigned(row.expected_2d_return, "%")}
                  </span>
                  <ArrowUpRight size={16} />
                  <small className="allocation-reason">{row.reason}</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="empty-state large">{plan.warnings[0]}</div>
          )}

          <details className="allocation-method">
            <summary>
              배분 기준과 주의사항
              <ChevronDown size={16} />
            </summary>
            <div>
              <section>
                <strong>적용한 방법</strong>
                {plan.methodology.map((item) => (
                  <p key={item}>• {item}</p>
                ))}
              </section>
              <section>
                <strong>반드시 확인</strong>
                {plan.warnings.map((item) => (
                  <p key={item}>• {item}</p>
                ))}
              </section>
            </div>
          </details>
        </section>
      )}

      <section className="portfolio-existing">
        <div className="section-heading">
          <div>
            <p className="eyebrow">CURRENT HOLDINGS</p>
            <h2>현재 보유 현황</h2>
          </div>
        </div>

        {summary && (
          <>
            <section className="currency-summary-grid">
              {summary.currency_summaries.map((row) => (
                <article className="panel" key={row.currency}>
                  <div className="section-heading">
                    <h2>{row.currency} 계좌</h2>
                  </div>
                  <div className="metric-grid compact">
                    <Metric label="매입금액" value={formatMoney(row.total_cost, row.currency)} />
                    <Metric label="평가금액" value={formatMoney(row.total_value, row.currency)} />
                    <Metric label="평가손익" value={formatMoney(row.total_pnl, row.currency)} />
                    <Metric
                      label="수익률"
                      value={
                        row.total_pnl_rate === null
                          ? "-"
                          : `${row.total_pnl_rate.toFixed(2)}%`
                      }
                    />
                  </div>
                </article>
              ))}
            </section>

            {summary.mixed_currencies && (
              <RiskAlert>
                원화와 달러 자산은 환율을 임의 적용하지 않고 통화별로 분리했습니다.
              </RiskAlert>
            )}
            {summary.concentration_warning && (
              <RiskAlert>
                <AlertTriangle size={16} /> 가장 큰 종목 비중이{" "}
                {summary.largest_position_weight.toFixed(1)}%입니다. 단일 종목 집중 위험을
                확인하세요.
              </RiskAlert>
            )}

            <section className="panel">
              <div className="section-heading">
                <h2>보유 자산</h2>
              </div>
              <div className="data-table">
                <div className="data-row header">
                  <span>종목</span>
                  <span>현재가</span>
                  <span>평가손익</span>
                  <span>수익률</span>
                  <span>비중</span>
                  <span />
                </div>
                {summary.positions.map((row) => (
                  <button
                    className="data-row"
                    key={row.holding_id}
                    type="button"
                    onClick={() => onOpenStock(row.ticker)}
                  >
                    <span>
                      <strong>{row.name}</strong>
                      <small>{row.ticker}</small>
                    </span>
                    <span>{row.current_price?.toLocaleString("ko-KR") ?? "-"}</span>
                    <span className={(row.pnl ?? 0) >= 0 ? "positive" : "negative"}>
                      {row.pnl?.toLocaleString("ko-KR") ?? "-"} {row.currency}
                    </span>
                    <span>{row.pnl_rate?.toFixed(2) ?? "-"}%</span>
                    <span>{row.weight.toFixed(1)}%</span>
                    <ArrowUpRight size={16} />
                  </button>
                ))}
              </div>
            </section>
          </>
        )}
      </section>
    </div>
  );
}

function AllocationMetric({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone?: "positive" | "negative";
}) {
  return (
    <div>
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatMoney(value: number, currency: string) {
  return `${value.toLocaleString("ko-KR", {
    maximumFractionDigits: currency === "KRW" ? 0 : 2,
  })} ${currency}`;
}

function formatSigned(value: number, suffix: string) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}${suffix}`;
}

function formatSignedMoney(value: number, currency: string) {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${formatMoney(Math.abs(value), currency)}`;
}
