import axios from "axios";

import type {
  AllocationPlan,
  AnalysisJob,
  BacktestSummary,
  DailyValidationRefreshResult,
  HistoricalReplayRun,
  MlTrainingResult,
  ModelOverview,
  ModelVersionInfo,
  PerformanceDiagnostics,
  PortfolioSummary,
  ResearchSummary,
  SchedulerState,
} from "../types/analytics";
import type { Holding, HoldingInput } from "../types/holding";
import type { StockChatResponse, StockChatStatus } from "../types/chat";
import type { Recommendation } from "../types/recommendation";
import type { DailyReport } from "../types/report";
import type { IntradayResponse, NewsArticle, PricePoint, StockResearch } from "../types/stock";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8010";
const api = axios.create({ baseURL: API_BASE, timeout: 300000 });

export const stockApi = {
  health: async () => (await api.get<{ status: string; version: string }>("/health")).data,
  holdings: async () => (await api.get<Holding[]>("/holdings")).data,
  addHolding: async (payload: HoldingInput) =>
    (await api.post<Holding>("/holdings", payload)).data,
  updateHolding: async (id: number, payload: Partial<HoldingInput>) =>
    (await api.put<Holding>(`/holdings/${id}`, payload)).data,
  deleteHolding: async (id: number) => api.delete(`/holdings/${id}`),
  startAnalysis: async (market = "ALL") =>
    (
      await api.post<{ success: boolean; job_id: number; message: string }>("/analyze/jobs", {
        market,
        include_recommendations: true,
        include_holdings: true,
      })
    ).data,
  analysisJob: async (id: number) => (await api.get<AnalysisJob>(`/analyze/jobs/${id}`)).data,
  analysisJobs: async () => (await api.get<AnalysisJob[]>("/analyze/jobs")).data,
  cancelAnalysis: async (id: number) =>
    (await api.post<AnalysisJob>(`/analyze/jobs/${id}/cancel`)).data,
  chatStatus: async () =>
    (await api.get<StockChatStatus>("/chat/status")).data,
  askStockChat: async (payload: {
    question: string;
    ticker?: string;
    history?: Array<{ role: "user" | "assistant"; content: string }>;
  }) => (await api.post<StockChatResponse>("/chat/ask", payload)).data,
  analyzeTicker: async (ticker: string) =>
    (
      await api.post<{
        success: boolean;
        ticker: string;
        report_id: number;
        data_available: boolean;
        message: string;
      }>(`/analyze/ticker/${encodeURIComponent(ticker)}`)
    ).data,
  reports: async () => (await api.get<DailyReport[]>("/reports/daily")).data,
  hiddenReports: async () =>
    (await api.get<Array<{ ticker: string; name: string; market: string }>>("/reports/dashboard/hidden"))
      .data,
  hideDashboardReport: async (ticker: string) =>
    (await api.post(`/reports/dashboard/${encodeURIComponent(ticker)}/hide`)).data,
  showDashboardReport: async (ticker: string) =>
    (await api.delete(`/reports/dashboard/${encodeURIComponent(ticker)}/hide`)).data,
  stockReport: async (ticker: string) => {
    try {
      return (await api.get<DailyReport>(`/reports/stock/${encodeURIComponent(ticker)}`)).data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) return null;
      throw error;
    }
  },
  recommendations: async () =>
    (await api.get<Recommendation[]>("/recommendations/today")).data,
  top5: async () => (await api.get<Recommendation[]>("/recommendations/top5")).data,
  refreshTop5: async () =>
    (
      await api.post<{ success: boolean; job_id: number; message: string }>(
        "/recommendations/top5/refresh",
      )
    ).data,
  prices: async (ticker: string) =>
    (await api.get<PricePoint[]>(`/stocks/${encodeURIComponent(ticker)}/prices`)).data,
  intraday: async (ticker: string) =>
    (await api.get<IntradayResponse>(`/stocks/${encodeURIComponent(ticker)}/intraday`)).data,
  news: async (ticker: string) =>
    (await api.get<NewsArticle[]>(`/stocks/${encodeURIComponent(ticker)}/news`)).data,
  research: async (ticker: string) =>
    (await api.get<StockResearch>(`/analytics/stocks/${encodeURIComponent(ticker)}/research`)).data,
  backtest: async (ticker?: string) =>
    (await api.get<BacktestSummary>("/analytics/backtest", { params: ticker ? { ticker } : undefined }))
      .data,
  startHistoricalReplay: async () =>
    (
      await api.post<{ success: boolean; run_id: number; message: string }>(
        "/analytics/backtest/replay",
        {
          lookback_years: 2,
          markets: ["KR", "US"],
          scope: "current_analysis_universe",
          horizon_days: 1,
          force_rebuild: false,
        },
      )
    ).data,
  latestHistoricalReplay: async () =>
    (await api.get<HistoricalReplayRun | null>("/analytics/backtest/replay/latest")).data,
  ensureDailyHistoricalReplay: async () =>
    (await api.post<DailyValidationRefreshResult>("/analytics/backtest/replay/ensure-daily"))
      .data,
  historicalReplay: async (runId: number) =>
    (await api.get<HistoricalReplayRun>(`/analytics/backtest/replay/${runId}`)).data,
  historicalReplayResults: async (runId: number) =>
    (
      await api.get<{ run: HistoricalReplayRun; summary: BacktestSummary }>(
        `/analytics/backtest/replay/${runId}/results`,
      )
    ).data,
  models: async () => (await api.get<ModelOverview>("/analytics/models")).data,
  performanceDiagnostics: async () =>
    (await api.get<PerformanceDiagnostics>("/analytics/performance/diagnostics")).data,
  researchSummary: async () =>
    (await api.get<ResearchSummary>("/analytics/research")).data,
  modelDetail: async (modelId: number) =>
    (await api.get<ModelVersionInfo>(`/analytics/models/${modelId}`)).data,
  trainMlCandidates: async () =>
    (await api.post<MlTrainingResult>("/analytics/models/train")).data,
  activateModel: async (modelId: number) =>
    (
      await api.post<ModelOverview>(`/analytics/models/${modelId}/activate`, {
        confirmed: true,
      })
    ).data,
  restoreBaselineModel: async () =>
    (await api.post<ModelOverview>("/analytics/models/baseline/activate")).data,
  portfolio: async () => (await api.get<PortfolioSummary>("/analytics/portfolio")).data,
  allocation: async (payload: {
    capital: number;
    currency: "KRW" | "USD";
    risk_profile: "low" | "medium" | "high";
    max_positions?: number;
  }) => (await api.post<AllocationPlan>("/analytics/allocation", payload)).data,
  alerts: async () => (await api.get("/analytics/alerts")).data,
  checkAlerts: async () => (await api.post("/analytics/alerts/check")).data,
  scheduler: async () => (await api.get<SchedulerState>("/analytics/scheduler")).data,
  reloadScheduler: async () => (await api.post<SchedulerState>("/analytics/scheduler/reload")).data,
  settings: async () =>
    (await api.get<Array<{ id: number; key: string; value: string }>>("/settings")).data,
  saveSetting: async (key: string, value: string) =>
    (await api.post("/settings", { key, value })).data,
  createBackup: async () => (await api.post("/maintenance/backup")).data,
  backups: async () =>
    (
      await api.get<Array<{ filename: string; size: number; modified_at: string }>>(
        "/maintenance/backups",
      )
    ).data,
  restoreBackup: async (filename: string) =>
    (await api.post(`/maintenance/restore/${encodeURIComponent(filename)}`)).data,
  cleanup: async () => (await api.post("/maintenance/cleanup")).data,
  reportsCsvUrl: `${API_BASE}/maintenance/reports.csv`,
};

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      (error.response?.data as { detail?: string } | undefined)?.detail ??
      "서버에 연결하지 못했습니다."
    );
  }
  return "알 수 없는 오류가 발생했습니다.";
}
