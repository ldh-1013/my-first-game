import { Activity, Database, EyeOff, Plus, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import StockCard from "../components/StockCard";
import type { AnalysisJob } from "../types/analytics";
import type { Holding } from "../types/holding";
import type { DailyReport } from "../types/report";

interface DashboardProps {
  onOpenStock: (ticker: string) => void;
}

export default function Dashboard({ onOpenStock }: DashboardProps) {
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [hidden, setHidden] = useState<Array<{ ticker: string; name: string; market: string }>>([]);
  const [serverOnline, setServerOnline] = useState(false);
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [message, setMessage] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [showHidden, setShowHidden] = useState(false);
  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [market, setMarket] = useState<"KR" | "US">("US");

  const load = async () => {
    const [health, reportRows, holdingRows, hiddenRows, jobs] = await Promise.allSettled([
      stockApi.health(),
      stockApi.reports(),
      stockApi.holdings(),
      stockApi.hiddenReports(),
      stockApi.analysisJobs(),
    ]);
    setServerOnline(health.status === "fulfilled");
    if (reportRows.status === "fulfilled") setReports(reportRows.value);
    if (holdingRows.status === "fulfilled") setHoldings(holdingRows.value);
    if (hiddenRows.status === "fulfilled") setHidden(hiddenRows.value);
    if (jobs.status === "fulfilled") {
      setJob(jobs.value.find((row) => ["queued", "running"].includes(row.status)) ?? null);
    }
  };

  useEffect(() => void load(), []);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await stockApi.analysisJob(job.id);
        setJob(next);
        if (!["queued", "running"].includes(next.status)) {
          setMessage(next.message);
          await load();
        }
      } catch (error) {
        setMessage(getApiError(error));
        await load();
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  const orderedReports = useMemo(() => {
    const holdingTickers = new Set(holdings.map((row) => canonicalTicker(row.ticker)));
    const seen = new Set<string>();
    return [...reports]
      .sort(
        (a, b) =>
          Number(holdingTickers.has(canonicalTicker(b.ticker))) -
            Number(holdingTickers.has(canonicalTicker(a.ticker))) || b.final_score - a.final_score,
      )
      .filter((row) => {
        const key = canonicalTicker(row.ticker);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
  }, [holdings, reports]);

  const startAnalysis = async () => {
    try {
      const result = await stockApi.startAnalysis();
      const next = await stockApi.analysisJob(result.job_id);
      setJob(next);
      setMessage(result.message);
    } catch (error) {
      setMessage(getApiError(error));
    }
  };

  const cancelAnalysis = async () => {
    if (!job) return;
    try {
      const next = await stockApi.cancelAnalysis(job.id);
      setJob(next);
      setMessage(next.message);
      await load();
    } catch (error) {
      setMessage(getApiError(error));
    }
  };

  const addStock = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const holding = await stockApi.addHolding({
        ticker: ticker.trim(),
        name: name.trim(),
        market_type: market,
        asset_type: "LISTED_STOCK",
        avg_buy_price: 0,
        quantity: 0,
        investment_memo: "대시보드 관심 종목",
        interest_level: 5,
        risk_tolerance: "medium",
        tags: ["관심"],
      });
      await stockApi.showDashboardReport(holding.ticker);
      const result = await stockApi.analyzeTicker(holding.ticker);
      setMessage(result.message);
      setTicker("");
      setName("");
      setShowAddForm(false);
      await load();
    } catch (error) {
      setMessage(getApiError(error));
    }
  };

  const restore = async (value: string) => {
    await stockApi.showDashboardReport(value);
    await load();
  };

  const averageScore = reports.length
    ? reports.reduce((sum, row) => sum + row.final_score, 0) / reports.length
    : 0;
  const reliable = reports.filter((row) => row.data_quality_score >= 70).length;
  const busy = Boolean(job && ["queued", "running"].includes(job.status));

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">MARKET PULSE · {new Date().toLocaleDateString("ko-KR")}</p>
          <h1>
            오늘의 신호를
            <br />
            <em>검증 가능한 형태로</em> 봅니다.
          </h1>
          <p className="hero-copy">
            가격·뉴스·재무·공시를 통합하고 데이터 품질과 예측 적중률을 함께 표시합니다.
          </p>
        </div>
        <button className="primary-button" onClick={startAnalysis} disabled={busy}>
          <RefreshCw className={busy ? "spin" : ""} size={18} />
          {busy ? "분석 진행 중" : "전체 분석 시작"}
        </button>
      </header>

      {message && <div className="status-message">{message}</div>}
      {job && busy && (
        <section className="panel job-panel">
          <div>
            <strong>{job.message}</strong>
            <span>
              {job.processed_items}/{job.total_items} · 실패 {job.failed_items}
            </span>
          </div>
          <div className="job-progress">
            <span style={{ width: `${job.progress_percent}%` }} />
          </div>
          <button className="ghost-button" onClick={cancelAnalysis}>
            <XCircle size={16} /> 중단
          </button>
        </section>
      )}

      <section className="metric-grid">
        <Metric icon={<Activity size={20} />} label="분석 종목" value={String(reports.length)} />
        <Metric icon={<ShieldCheck size={20} />} label="신뢰 데이터" value={String(reliable)} />
        <Metric icon={<Activity size={20} />} label="평균 점수" value={averageScore.toFixed(1)} />
        <Metric
          icon={<Database size={20} />}
          label="로컬 API"
          value={serverOnline ? "ONLINE" : "OFFLINE"}
        />
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">TODAY REPORTS</p>
            <h2>오늘의 종목 리포트</h2>
          </div>
          <div className="inline-actions">
            <button className="ghost-button" onClick={() => setShowHidden((value) => !value)}>
              <EyeOff size={16} /> 숨긴 종목 {hidden.length}
            </button>
            <button className="ghost-button" onClick={() => setShowAddForm((value) => !value)}>
              <Plus size={16} /> 종목 추가
            </button>
          </div>
        </div>

        {showHidden && (
          <div className="hidden-manager panel">
            <strong>숨긴 종목 관리</strong>
            {hidden.length ? (
              hidden.map((row) => (
                <button key={row.ticker} onClick={() => restore(row.ticker)}>
                  {row.name} · {row.ticker} <span>복원</span>
                </button>
              ))
            ) : (
              <span>숨긴 종목이 없습니다.</span>
            )}
          </div>
        )}

        {showAddForm && (
          <form className="quick-stock-form" onSubmit={addStock}>
            <label>
              시장
              <select value={market} onChange={(event) => setMarket(event.target.value as "KR" | "US")}>
                <option value="US">미국</option>
                <option value="KR">한국</option>
              </select>
            </label>
            <label>
              종목 코드
              <input
                required
                value={ticker}
                placeholder={market === "KR" ? "005930" : "NVDA"}
                onChange={(event) => setTicker(event.target.value)}
              />
            </label>
            <label>
              종목명
              <input required value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <button className="primary-button" type="submit">
              추가 후 분석
            </button>
          </form>
        )}

        {orderedReports.length ? (
          <div className="stock-grid">
            {orderedReports.map((report) => (
              <StockCard
                key={report.id}
                report={report}
                onOpen={onOpenStock}
                onRemove={async (value) => {
                  await stockApi.hideDashboardReport(value);
                  await load();
                }}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state large">분석을 실행하거나 원하는 종목을 추가해 주세요.</div>
        )}
      </section>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="metric-card">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function canonicalTicker(ticker: string) {
  return ticker.toUpperCase().replace(/\.(KS|KQ)$/, "");
}
