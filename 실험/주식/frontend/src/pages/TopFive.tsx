import { RefreshCw, Trophy, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import RiskAlert from "../components/RiskAlert";
import TopFiveCardGrid from "../components/TopFiveCardGrid";
import type { AnalysisJob } from "../types/analytics";
import type { Recommendation } from "../types/recommendation";

export default function TopFive({ onOpenStock }: { onOpenStock: (ticker: string) => void }) {
  const [rows, setRows] = useState<Recommendation[]>([]);
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setRows(await stockApi.top5());
      setError("");
    } catch (loadError) {
      setError(getApiError(loadError));
    }
  };

  useEffect(() => void load(), []);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await stockApi.analysisJob(job.id);
        setJob(next);
        if (!["queued", "running"].includes(next.status)) await load();
      } catch (pollError) {
        setError(getApiError(pollError));
        await load();
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  const refreshMarket = async () => {
    try {
      const result = await stockApi.refreshTop5();
      setJob(await stockApi.analysisJob(result.job_id));
      setError("");
    } catch (refreshError) {
      setError(getApiError(refreshError));
    }
  };

  const cancelAnalysis = async () => {
    if (!job) return;
    try {
      const next = await stockApi.cancelAnalysis(job.id);
      setJob(next);
      setError("");
      await load();
    } catch (cancelError) {
      setError(getApiError(cancelError));
    }
  };

  const busy = Boolean(job && ["queued", "running"].includes(job.status));
  return (
    <div className="page top5-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">GLOBAL UPSIDE RANKING</p>
          <h1>한국·미국 통합 TOP 5</h1>
          <p>
            보유 여부와 관계없이 한국·미국 상장종목을 동일한 가격 추세·거래량·변동성
            기준으로 비교합니다.
          </p>
        </div>
        <div className="inline-actions">
          <div className="top5-emblem"><Trophy size={25} /> TOP 5</div>
          <button className="ghost-button" onClick={refreshMarket} disabled={busy}>
            <RefreshCw className={busy ? "spin" : ""} size={16} />
            {busy ? "시장 스캔 중" : "시장 다시 스캔"}
          </button>
        </div>
      </header>

      {error && <div className="error-message">{error}</div>}
      {busy && job && (
        <section className="panel job-panel">
          <div>
            <strong>{job.message}</strong>
            <span>{job.processed_items}/{job.total_items} · 실패 {job.failed_items}</span>
          </div>
          <div className="job-progress"><span style={{ width: `${job.progress_percent}%` }} /></div>
          <button className="ghost-button" onClick={cancelAnalysis}>
            <XCircle size={16} /> 중단
          </button>
        </section>
      )}

      <RiskAlert>
        보유종목은 순위 계산에 사용하지 않습니다. 급등 종목은 제외하지 않고
        <strong> 급등 주의</strong>로 표시합니다.
      </RiskAlert>

      <TopFiveCardGrid
        rows={rows}
        onOpen={onOpenStock}
        emptyMessage="저장된 시장 데이터가 부족합니다. ‘시장 다시 스캔’을 눌러 주세요."
      />
    </div>
  );
}
