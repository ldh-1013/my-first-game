import {
  Activity,
  BarChart3,
  BookOpen,
  BrainCircuit,
  CalendarRange,
  CheckCircle2,
  Clock3,
  Cpu,
  Eye,
  FlaskConical,
  Gauge,
  GitCompare,
  Play,
  RotateCcw,
  ShieldCheck,
  Target,
} from "lucide-react";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { getApiError, stockApi } from "../api/client";
import RiskAlert from "../components/RiskAlert";
import type {
  BacktestSummary,
  HistoricalReplayRun,
  ModelOverview,
  ModelVersionInfo,
  PerformanceDiagnostics,
  ResearchSummary,
  SchedulerState,
} from "../types/analytics";

const RUNNING_STATUSES = new Set(["queued", "running"]);

export default function Analytics() {
  const [data, setData] = useState<BacktestSummary | null>(null);
  const [run, setRun] = useState<HistoricalReplayRun | null>(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);
  const [models, setModels] = useState<ModelOverview | null>(null);
  const [trainingMl, setTrainingMl] = useState(false);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [mlView, setMlView] = useState<"summary" | "performance" | "compare">("summary");
  const [mlMessage, setMlMessage] = useState("");
  const [confirmModel, setConfirmModel] = useState<ModelVersionInfo | null>(null);
  const [diagnostics, setDiagnostics] = useState<PerformanceDiagnostics | null>(null);
  const [research, setResearch] = useState<ResearchSummary | null>(null);
  const [scheduler, setScheduler] = useState<SchedulerState | null>(null);

  const refreshSummary = useCallback(async () => {
    setData(await stockApi.backtest());
  }, []);

  useEffect(() => {
    Promise.all([
      refreshSummary(),
      stockApi.models().then(setModels),
      stockApi.performanceDiagnostics().then(setDiagnostics),
      stockApi.researchSummary().then(setResearch),
      stockApi.scheduler().then(setScheduler),
      stockApi.ensureDailyHistoricalReplay().then((result) => setRun(result.run)),
    ]).catch((err) => setError(getApiError(err)));
  }, [refreshSummary]);

  useEffect(() => {
    if (!models || selectedModelId !== null) return;
    const preferred =
      models.models.find((model) => model.recommended && model.can_activate) ??
      models.models.find((model) => model.can_activate) ??
      models.active_model;
    setSelectedModelId(preferred.id);
  }, [models, selectedModelId]);

  useEffect(() => {
    if (!run || !RUNNING_STATUSES.has(run.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = await stockApi.historicalReplay(run.id);
        setRun(next);
        if (!RUNNING_STATUSES.has(next.status)) {
          await refreshSummary();
        }
      } catch (err) {
        setError(getApiError(err));
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [run?.id, run?.status, refreshSummary]);

  const startReplay = async () => {
    setStarting(true);
    setError("");
    try {
      const created = await stockApi.startHistoricalReplay();
      setRun(await stockApi.historicalReplay(created.run_id));
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setStarting(false);
    }
  };

  const isRunning = starting || Boolean(run && RUNNING_STATUSES.has(run.status));

  const trainMlCandidates = async () => {
    setTrainingMl(true);
    setError("");
    setMlMessage("");
    try {
      const result = await stockApi.trainMlCandidates();
      setModels(result.overview);
      setMlMessage(result.message);
      const recommended = result.overview.models.find((model) => model.recommended);
      if (recommended) setSelectedModelId(recommended.id);
      setMlView("compare");
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setTrainingMl(false);
    }
  };

  const applyCandidate = async () => {
    if (!confirmModel) return;
    try {
      const next = await stockApi.activateModel(confirmModel.id);
      setModels(next);
      setMlMessage(`${confirmModel.version_name} 모델을 운영 예측 모델로 적용했습니다.`);
      setConfirmModel(null);
    } catch (err) {
      setError(getApiError(err));
    }
  };

  const restoreBaseline = async () => {
    try {
      const next = await stockApi.restoreBaselineModel();
      setModels(next);
      setSelectedModelId(next.active_model.id);
      setMlMessage("규칙 기반 기준 모델로 되돌렸습니다.");
    } catch (err) {
      setError(getApiError(err));
    }
  };

  return (
    <div className="page analytics-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">PREDICTION AUDIT</p>
          <h1>예측 검증</h1>
          <p>
            과거 거래일마다 현재 예측 엔진을 다시 실행해 다음 실제 거래일 결과와 비교합니다.
          </p>
        </div>
        <button className="primary-button replay-button" onClick={startReplay} disabled={isRunning}>
          <Play size={17} />
          {isRunning ? "과거 재현 검증 진행 중" : "최근 2년 과거 재현 검증 실행"}
        </button>
      </header>

      <section className="replay-explainer">
        <FlaskConical size={20} />
        <div>
          <strong>역사적 예측 시뮬레이션 · 워크포워드 검증</strong>
          <p>
            이 화면은 과거 거래일에 현재 예측 엔진을 재현 실행한 결과입니다. 실제 과거
            실시간 예측 기록이 아니며, 과거 성과는 미래 결과를 보장하지 않습니다.
          </p>
          <small>
            과거 뉴스·재무 스냅샷이 시점 기준으로 없으면 현재 데이터를 끼워 넣지 않고 중립
            점수로 처리합니다.
          </small>
        </div>
      </section>

      {scheduler && <AutoValidationStatus scheduler={scheduler} run={run} />}

      {error && <div className="error-message">{error}</div>}
      {run && <ReplayProgress run={run} />}

      {data && (
        <>
          <section className="metric-grid replay-metrics">
            <Metric
              icon={<Gauge />}
              label="과거 재현 평가 표본"
              value={`${data.evaluated.toLocaleString()}건`}
              hint={`최소 참고 ${data.minimum_recommended_samples}건`}
            />
            <Metric
              icon={<CheckCircle2 />}
              label="방향 적중률"
              value={percent(data.accuracy)}
              hint={`보합 제외 ${data.direction_evaluated.toLocaleString()}건`}
            />
            <Metric
              icon={<Clock3 />}
              label="평균 절대오차"
              value={data.mean_absolute_error === null ? "-" : `${data.mean_absolute_error.toFixed(2)}%p`}
              hint="예측 범위 중심값 기준"
            />
            <Metric
              icon={<Target />}
              label="예상 범위 적중률"
              value={percent(data.range_accuracy)}
              hint="예상 하단~상단 포함"
            />
            <Metric
              icon={<Activity />}
              label="최근 3개월 적중률"
              value={percent(data.recent_3m_accuracy)}
              hint="최근 시장 환경 반영"
            />
            <Metric
              icon={<CalendarRange />}
              label="최근 2년 적중률"
              value={percent(data.recent_2y_accuracy)}
              hint="전체 워크포워드 구간"
            />
            <Metric
              icon={<ShieldCheck />}
              label="보정 상태"
              value={calibrationLabel(data.calibration_status)}
              hint={`높은 신뢰도 검토 ${data.high_confidence_review_samples}건 이상`}
            />
          </section>

          {data.status === "collecting" && (
            <RiskAlert>
              <strong>표본 부족</strong>
              <br />
              현재 신뢰도 보정에 사용할 수 있는 과거 재현 데이터가 충분하지 않습니다.
              최소 {data.minimum_recommended_samples}건부터 참고하고,{" "}
              {data.high_confidence_review_samples}건 이상에서 높은 신뢰도 여부를 검토합니다.
            </RiskAlert>
          )}

          <CandidateModelPanel model={data.candidate_model} />

          {models && (
            <MlCandidatePanel
              overview={models}
              selectedModelId={selectedModelId}
              onSelectModel={setSelectedModelId}
              view={mlView}
              onViewChange={setMlView}
              training={trainingMl}
              message={mlMessage}
              onTrain={trainMlCandidates}
              onApply={setConfirmModel}
              onRestoreBaseline={restoreBaseline}
            />
          )}

          {diagnostics && (
            <PerformanceDiagnosticsPanel diagnostics={diagnostics} research={research} />
          )}

          <section className="panel replay-results">
            <div className="section-heading">
              <div>
                <p className="eyebrow">HISTORICAL REPLAY SAMPLES</p>
                <h2>과거 재현 표본</h2>
              </div>
              <span className="soft-badge">최근 {data.details.length.toLocaleString()}건 표시</span>
            </div>
            <div className="replay-table-scroll">
              <div className="data-table replay-table">
                <div className="data-row header">
                  <span>종목</span>
                  <span>예측일</span>
                  <span>실제 대상일</span>
                  <span>원본 상승</span>
                  <span>보정 상승</span>
                  <span>예상 변동 범위</span>
                  <span>실제 수익률</span>
                  <span>방향</span>
                  <span>범위</span>
                  <span>절대오차</span>
                  <span>데이터 상태</span>
                </div>
                {data.details.map((row, index) => (
                  <div className="data-row" key={`${row.ticker}-${row.prediction_date}-${index}`}>
                    <span>
                      <strong>{row.name}</strong>
                      <small>
                        {row.ticker} · {row.market}
                      </small>
                    </span>
                    <span>{row.prediction_date}</span>
                    <span>{row.target_date ?? "-"}</span>
                    <span>{row.up_probability.toFixed(1)}%</span>
                    <span>{row.calibrated_up_probability.toFixed(1)}%</span>
                    <span>
                      {signed(row.expected_range_low)} ~ {signed(row.expected_range_high)}
                    </span>
                    <span className={(row.actual_return ?? 0) >= 0 ? "positive" : "negative"}>
                      {row.actual_return === null ? "-" : signed(row.actual_return)}
                    </span>
                    <span>{hitLabel(row.is_correct, row.actual_direction === "flat")}</span>
                    <span>{hitLabel(row.range_hit)}</span>
                    <span>{row.absolute_error === null ? "-" : `${row.absolute_error.toFixed(2)}%p`}</span>
                    <span className="data-quality-cell">{dataQualityLabel(row)}</span>
                  </div>
                ))}
                {!data.details.length && (
                  <div className="empty-state">
                    과거 재현 표본이 없습니다. 위 버튼을 눌러 최근 2년 워크포워드 검증을
                    시작하세요.
                  </div>
                )}
              </div>
            </div>
          </section>
        </>
      )}
      {confirmModel && (
        <div className="model-confirm-backdrop" role="presentation">
          <section className="model-confirm-dialog" role="dialog" aria-modal="true">
            <div className="model-confirm-icon">
              <ShieldCheck size={22} />
            </div>
            <h2>후보 모델을 운영 모델로 적용할까요?</h2>
            <p>
              이 모델은 과거 검증 성능을 기반으로 한 후보입니다. 미래 성과를 보장하지 않으며,
              운영 모델 변경은 사용자의 책임입니다.
            </p>
            <strong>{confirmModel.version_name}</strong>
            <div className="inline-actions">
              <button className="secondary-button" onClick={() => setConfirmModel(null)}>
                취소
              </button>
              <button className="primary-button" onClick={applyCandidate}>
                내용을 확인했으며 적용
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function AutoValidationStatus({
  scheduler,
  run,
}: {
  scheduler: SchedulerState;
  run: HistoricalReplayRun | null;
}) {
  const validation = scheduler.prediction_validation;
  const running = run ? RUNNING_STATUSES.has(run.status) : false;
  const nextRun = validation?.next_run_time
    ? new Date(validation.next_run_time).toLocaleString("ko-KR")
    : "예약 없음";
  const statusText = running
    ? "오늘자 예측 검증을 자동 갱신 중입니다."
    : run?.status === "completed"
      ? "최신 예측 검증 데이터가 준비되었습니다."
      : run?.status === "failed"
        ? "최근 자동 갱신이 실패했습니다. 다음 예약 시간에 다시 시도합니다."
        : "예측 검증 데이터를 준비 중입니다.";

  return (
    <section className="auto-validation-card">
      <div>
        <span className={`status-dot ${running ? "running" : run?.status ?? "queued"}`} />
        <div>
          <strong>예측 검증 자동 최신화 {validation?.enabled ? "켜짐" : "꺼짐"}</strong>
          <p>{statusText}</p>
        </div>
      </div>
      <div>
        <span>다음 자동 실행</span>
        <strong>{nextRun}</strong>
      </div>
      {run && (
        <div>
          <span>최근 검증 범위</span>
          <strong>
            {run.start_date} ~ {run.end_date}
          </strong>
        </div>
      )}
    </section>
  );
}

function MlCandidatePanel({
  overview,
  selectedModelId,
  onSelectModel,
  view,
  onViewChange,
  training,
  message,
  onTrain,
  onApply,
  onRestoreBaseline,
}: {
  overview: ModelOverview;
  selectedModelId: number | null;
  onSelectModel: (id: number) => void;
  view: "summary" | "performance" | "compare";
  onViewChange: (view: "summary" | "performance" | "compare") => void;
  training: boolean;
  message: string;
  onTrain: () => void;
  onApply: (model: ModelVersionInfo) => void;
  onRestoreBaseline: () => void;
}) {
  const selected =
    overview.models.find((model) => model.id === selectedModelId) ?? overview.active_model;
  const experiment = overview.experiments.find(
    (row) => row.model_type === selected.model_type,
  );
  const baseline = selected.test_summary.baseline;
  const test = selected.test_summary;
  const classifierModels = overview.models.filter(
    (model) =>
      model.model_type !== "baseline" &&
      model.model_type !== "hist_gradient_boosting_regressor",
  );

  return (
    <section className="panel ml-candidate-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MACHINE LEARNING CANDIDATES</p>
          <h2>ML 후보 모델 비교</h2>
        </div>
        <span className="active-model-badge">
          <Cpu size={15} />
          현재 활성: {modelName(overview.active_model)}
        </span>
      </div>

      <div className="ml-action-bar">
        <button className="primary-button" onClick={onTrain} disabled={training}>
          <BrainCircuit size={17} />
          {training ? "시간순 학습·검증 중" : "ML 후보 모델 학습"}
        </button>
        <button
          className={view === "performance" ? "secondary-button active" : "secondary-button"}
          onClick={() => onViewChange("performance")}
        >
          <Eye size={16} />
          후보 모델 성능 보기
        </button>
        <button
          className={view === "compare" ? "secondary-button active" : "secondary-button"}
          onClick={() => onViewChange("compare")}
        >
          <GitCompare size={16} />
          기준 모델과 비교
        </button>
        <button
          className="secondary-button"
          disabled={!selected.can_activate || selected.is_active}
          onClick={() => onApply(selected)}
        >
          후보 모델 적용
        </button>
        <button
          className="secondary-button"
          disabled={overview.active_model.model_type === "baseline"}
          onClick={onRestoreBaseline}
        >
          <RotateCcw size={16} />
          운영 모델로 되돌리기
        </button>
      </div>

      {message && <div className="ml-result-message">{message}</div>}

      <div className="ml-model-selector" role="list">
        {classifierModels.length ? (
          classifierModels.map((model) => (
            <button
              key={model.id}
              className={model.id === selected.id ? "selected" : ""}
              onClick={() => onSelectModel(model.id)}
            >
              <span>{modelName(model)}</span>
              <small>
                {statusLabel(model.status)}
                {model.recommended ? " · 추천 후보" : ""}
              </small>
            </button>
          ))
        ) : (
          <p>아직 학습된 ML 방향성 후보가 없습니다.</p>
        )}
      </div>

      <div className="ml-summary-grid">
        <div>
          <span>기준 모델</span>
          <strong>{overview.baseline_version}</strong>
        </div>
        <div>
          <span>후보 모델</span>
          <strong>{selected.model_type === "baseline" ? "-" : modelName(selected)}</strong>
        </div>
        <div>
          <span>훈련 기간</span>
          <strong>{dateRange(experiment?.train_start_date, experiment?.train_end_date)}</strong>
          <small>{selected.training_summary.samples?.toLocaleString() ?? 0}건</small>
        </div>
        <div>
          <span>보정 기간</span>
          <strong>
            {dateRange(experiment?.calibration_start_date, experiment?.calibration_end_date)}
          </strong>
          <small>{selected.validation_summary.samples?.toLocaleString() ?? 0}건</small>
        </div>
        <div>
          <span>최종 테스트 기간</span>
          <strong>{dateRange(experiment?.test_start_date, experiment?.test_end_date)}</strong>
          <small>{test.samples?.toLocaleString() ?? 0}건</small>
        </div>
        <div>
          <span>후보 상태</span>
          <strong>{statusLabel(selected.status)}</strong>
          <small>
            추천 여부: {selected.recommended ? "추천 후보" : "참고"} · 자동 적용: 꺼짐
          </small>
        </div>
      </div>

      {view !== "summary" && (
        <div className="ml-metric-table">
          <div className="ml-metric-row header">
            <span>평가 지표</span>
            <span>기준 모델</span>
            <span>{modelName(selected)}</span>
            <span>판정</span>
          </div>
          {[
            ["방향 적중률", baseline?.accuracy, test.accuracy, true, "%"],
            ["Brier Score", baseline?.brier_score, test.brier_score, false, ""],
            [
              "Expected Calibration Error",
              baseline?.expected_calibration_error,
              test.expected_calibration_error,
              false,
              "",
            ],
            ["ROC-AUC", baseline?.roc_auc, test.roc_auc, true, ""],
            ["PR-AUC", baseline?.pr_auc, test.pr_auc, true, ""],
            ["상승 정밀도", baseline?.precision_up, test.precision_up, true, "%"],
            ["상승 재현율", baseline?.recall_up, test.recall_up, true, "%"],
            ["하락 정밀도", baseline?.precision_down, test.precision_down, true, "%"],
            ["하락 재현율", baseline?.recall_down, test.recall_down, true, "%"],
            ["F1 Score", baseline?.f1, test.f1, true, ""],
            ["Macro F1", baseline?.f1_macro, test.f1_macro, true, ""],
            ["Log Loss", baseline?.log_loss, test.log_loss, false, ""],
            [
              "평균 절대오차",
              baseline?.mean_absolute_error,
              test.mean_absolute_error,
              false,
              "%p",
            ],
          ].map(([label, baseValue, candidateValue, higherBetter, suffix]) => (
            <MetricComparisonRow
              key={String(label)}
              label={String(label)}
              baseline={typeof baseValue === "number" ? baseValue : null}
              candidate={typeof candidateValue === "number" ? candidateValue : null}
              higherBetter={Boolean(higherBetter)}
              suffix={String(suffix)}
            />
          ))}
        </div>
      )}

      {view === "performance" && test.walk_forward && (
        <div className="walk-forward-status">
          <span>월별 워크포워드 검증</span>
          <strong>{test.walk_forward.month_count}개월</strong>
          <small>
            최저 적중률 {formatMetric(test.walk_forward.worst_accuracy, "%")} · 변동성{" "}
            {formatMetric(
              test.walk_forward.accuracy_std == null
                ? null
                : test.walk_forward.accuracy_std * 100,
              "%p",
            )}{" "}
            · {test.walk_forward.stable ? "안정성 기준 통과" : "안정성 기준 미달"}
          </small>
        </div>
      )}

      {view === "performance" && test.high_confidence && (
        <div className="high-confidence-summary">
          <div>
            <span>고신뢰 기준</span>
            <strong>{(test.high_confidence.threshold * 100).toFixed(0)}%</strong>
          </div>
          <div>
            <span>선택 신호 적중률</span>
            <strong>{formatMetric(test.high_confidence.accuracy, "%")}</strong>
          </div>
          <div>
            <span>신호 빈도</span>
            <strong>{formatMetric(test.high_confidence.signal_frequency, "%")}</strong>
          </div>
          <div>
            <span>비용 차감 평균</span>
            <strong>{formatMetric(test.high_confidence.average_net_return, "%")}</strong>
          </div>
        </div>
      )}

      {test.candidate_criteria && (
        <div className="candidate-criteria">
          <strong>후보 승격 기준</strong>
          {test.candidate_criteria.mode && (
            <b>
              통과 유형:{" "}
              {test.candidate_criteria.mode === "selective_high_confidence"
                ? "고신뢰 선택 신호 전용"
                : "전체 방향 예측"}
            </b>
          )}
          {test.candidate_criteria.reasons.map((reason) => (
            <span key={reason}>{reason}</span>
          ))}
          <small>후보가 되어도 운영 모델로 자동 전환되지 않습니다.</small>
        </div>
      )}

      <div className="ml-data-limit">
        현재 ML 후보는 과거 시점에 확보된 가격·거래량·기술 지표 중심으로 학습되었습니다.
        과거 뉴스 또는 재무 데이터가 부족한 구간은 해당 값을 중립값으로 해석하지 않고
        결측치와 가용 여부 피처로 처리했습니다. 뉴스·공시·재무 영향은 별도 데이터 확보 후
        추가 검증이 필요합니다.
      </div>
    </section>
  );
}

function MetricComparisonRow({
  label,
  baseline,
  candidate,
  higherBetter,
  suffix,
}: {
  label: string;
  baseline: number | null;
  candidate: number | null;
  higherBetter: boolean;
  suffix: string;
}) {
  const improved =
    baseline !== null &&
    candidate !== null &&
    (higherBetter ? candidate > baseline : candidate < baseline);
  return (
    <div className="ml-metric-row">
      <span>{label}</span>
      <span>{formatMetric(baseline, suffix)}</span>
      <strong>{formatMetric(candidate, suffix)}</strong>
      <span className={improved ? "positive" : "muted"}>
        {baseline === null || candidate === null ? "-" : improved ? "개선" : "유지·미달"}
      </span>
    </div>
  );
}

function PerformanceDiagnosticsPanel({
  diagnostics,
  research,
}: {
  diagnostics: PerformanceDiagnostics;
  research: ResearchSummary | null;
}) {
  const signal = diagnostics.selective_signal;
  const segmentGroups = [
    ["시장", diagnostics.segments.market],
    ["시장 국면", diagnostics.segments.market_regime],
    ["변동성", diagnostics.segments.volatility],
    ["유동성", diagnostics.segments.liquidity],
  ] as const;

  return (
    <section className="panel performance-diagnostics">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MODEL DIAGNOSTICS</p>
          <h2>예측 성능 정밀 진단</h2>
        </div>
        <span className="soft-badge">
          <BarChart3 size={14} />
          {diagnostics.as_of_date ?? "표본 수집 중"}
        </span>
      </div>

      <div className="diagnostic-method">
        <strong>{diagnostics.methodology.prediction_timing}</strong>
        <p>{diagnostics.methodology.target}</p>
        <small>
          {diagnostics.methodology.flat_handling} · {diagnostics.methodology.market_regime_basis}
        </small>
      </div>

      <div className="diagnostic-kpi-grid">
        <DiagnosticKpi
          label="전체 방향 표본"
          value={`${diagnostics.methodology.direction_sample_count.toLocaleString()}건`}
          hint={`보합 제외 ${diagnostics.methodology.flat_excluded.toLocaleString()}건`}
        />
        <DiagnosticKpi
          label="±1% 이상 적중률"
          value={formatMetric(diagnostics.overall.meaningful_move?.accuracy, "%")}
          hint={`${diagnostics.overall.meaningful_move?.samples?.toLocaleString() ?? 0}건`}
        />
        <DiagnosticKpi
          label="고신뢰 신호 적중률"
          value={formatMetric(signal.accuracy, "%")}
          hint={`확률 기준 ${formatMetric((signal.threshold ?? 0) * 100, "%")}`}
        />
        <DiagnosticKpi
          label="신호 발생 비율"
          value={formatMetric(signal.signal_frequency, "%")}
          hint={`${signal.trades?.toLocaleString() ?? 0}회 거래`}
        />
        <DiagnosticKpi
          label="비용 차감 평균"
          value={formatMetric(signal.average_net_return, "%")}
          hint={`왕복 비용 ${signal.transaction_cost_percent ?? 0.2}% 가정`}
        />
        <DiagnosticKpi
          label="최대 낙폭"
          value={formatMetric(signal.maximum_drawdown, "%")}
          hint={`Sharpe ${formatMetric(signal.sharpe, "")}`}
        />
      </div>
      <p className="diagnostic-return-note">{diagnostics.methodology.return_curve_note}</p>

      <div className="diagnostic-columns">
        <section>
          <h3>기간별 성능</h3>
          <div className="diagnostic-list">
            {diagnostics.periods.map((period) => (
              <div key={period.period}>
                <span>{period.period}</span>
                <strong>{formatMetric(period.accuracy, "%")}</strong>
                <small>{period.samples.toLocaleString()}건</small>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h3>시점 누수 점검</h3>
          <div className="leakage-list">
            {diagnostics.leakage_audit.map((item) => (
              <div key={item.item}>
                <span className={item.status}>{item.status === "pass" ? "통과" : "제한"}</span>
                <p>
                  <strong>{item.item}</strong>
                  <small>{item.evidence}</small>
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="segment-grid">
        {segmentGroups.map(([label, rows]) => (
          <section key={label}>
            <h3>{label} 구간</h3>
            {rows.map((row) => (
              <div className="segment-row" key={row.segment}>
                <span>{regimeLabel(row.segment)}</span>
                <strong>{row.accuracy.toFixed(1)}%</strong>
                <small>{row.samples.toLocaleString()}건</small>
              </div>
            ))}
          </section>
        ))}
      </div>

      {research && (
        <details className="research-details">
          <summary>
            <BookOpen size={16} />
            적용한 검증 원칙과 외부 연구 근거
          </summary>
          <div className="research-principles">
            {research.principles.map((principle) => (
              <span key={principle}>{principle}</span>
            ))}
          </div>
          <div className="research-grid">
            {research.references.map((reference) => (
              <a href={reference.url} target="_blank" rel="noreferrer" key={reference.url}>
                <strong>{reference.title}</strong>
                <small>
                  {reference.author} · {reference.date}
                </small>
                <p>{reference.application}</p>
                <em>한계: {reference.limitation}</em>
              </a>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}

function DiagnosticKpi({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

function regimeLabel(value: string) {
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

function CandidateModelPanel({ model }: { model: BacktestSummary["candidate_model"] }) {
  const componentLabels: Record<string, string> = {
    news_score: "뉴스",
    technical_score: "기술",
    volume_score: "거래량",
    financial_score: "재무",
    risk_score: "리스크",
  };
  return (
    <section className="panel candidate-model-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">OUT-OF-SAMPLE WEIGHT CHECK</p>
          <h2>가중치 개선 후보 검증</h2>
        </div>
        <span className={`candidate-status ${model.status}`}>
          {model.status === "candidate"
            ? "후보 발견"
            : model.status === "not_improved"
              ? "개선 확인 안 됨"
              : "표본 부족"}
        </span>
      </div>
      <p>{model.message}</p>
      <div className="candidate-summary-grid">
        <div>
          <span>훈련 구간</span>
          <strong>{model.training_samples.toLocaleString()}건</strong>
          <small>앞 15개월</small>
        </div>
        <div>
          <span>검증 구간</span>
          <strong>{model.validation_samples.toLocaleString()}건</strong>
          <small>뒤 9개월</small>
        </div>
        <div>
          <span>운영 모델 검증</span>
          <strong>
            {model.baseline_validation_accuracy == null
              ? "-"
              : `${model.baseline_validation_accuracy.toFixed(1)}%`}
          </strong>
          <small>별도 검증 구간</small>
        </div>
        <div>
          <span>후보 모델 검증</span>
          <strong>
            {model.candidate_validation_accuracy == null
              ? "-"
              : `${model.candidate_validation_accuracy.toFixed(1)}%`}
          </strong>
          <small>{model.name ?? "후보 계산 전"}</small>
        </div>
      </div>
      {Object.keys(model.component_performance).length > 0 && (
        <div className="component-performance">
          <span>검증 구간 점수·실제 수익률 상관</span>
          <div>
            {Object.entries(model.component_performance).map(([key, value]) => (
              <small key={key}>
                {componentLabels[key] ?? key} {value === null ? "-" : value.toFixed(3)}
              </small>
            ))}
          </div>
        </div>
      )}
      <div className="candidate-safety-note">
        운영 가중치는 자동 변경하지 않았습니다. 후보가 발견되어도 사용자가 별도로 적용하기
        전까지 현재 모델을 유지합니다.
      </div>
    </section>
  );
}

function ReplayProgress({ run }: { run: HistoricalReplayRun }) {
  const loading = run.stage === "loading_prices";
  return (
    <section className="panel replay-progress-card">
      <div>
        <span className={`status-dot ${run.status}`} />
        <div>
          <strong>
            {run.status === "completed"
              ? "과거 재현 검증 완료"
              : run.status === "failed"
                ? "과거 재현 검증 실패"
                : loading
                  ? "종목별 과거 가격 준비 중"
                  : "과거 재현 검증 진행 중"}
          </strong>
          <small>
            {run.current_ticker ?? "대기 중"}
            {run.current_date ? ` · ${run.current_date}` : ""}
          </small>
        </div>
      </div>
      <div>
        <div className="progress-labels">
          <span>
            완료 {run.completed_tasks.toLocaleString()} · 실패 {run.failed_tasks.toLocaleString()}
          </span>
          <strong>{run.progress_percent.toFixed(1)}%</strong>
        </div>
        <div className="job-progress">
          <span style={{ width: `${run.progress_percent}%` }} />
        </div>
      </div>
      <small>
        {loading
          ? "각 종목의 약 3년 가격을 한 번씩 불러와 기술지표 워밍업 구간을 준비합니다."
          : `전체 ${run.total_tasks.toLocaleString()}개 거래일 표본`}
      </small>
    </section>
  );
}

function Metric({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <article className="metric-card replay-metric">
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  );
}

function percent(value: number | null) {
  return value === null ? "수집 중" : `${value.toFixed(1)}%`;
}

function signed(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function hitLabel(value: boolean | null, flat = false) {
  if (flat) return "보합";
  if (value === null) return "-";
  return value ? "적중" : "이탈";
}

function calibrationLabel(status: BacktestSummary["calibration_status"]) {
  if (status === "high_sample_review") return "고표본 검토";
  if (status === "reference_available") return "참고 가능";
  return "표본 부족";
}

function dataQualityLabel(row: BacktestSummary["details"][number]) {
  const labels = ["가격·기술지표 기반 재현"];
  labels.push(row.historical_news_available ? "과거 뉴스 포함" : "뉴스 과거 데이터 없음");
  labels.push(row.historical_financial_available ? "과거 재무 포함" : "재무 과거 데이터 없음");
  if (row.data_quality_note.includes("incomplete")) labels.push("데이터 불완전");
  return labels.join(" · ");
}

function modelName(model: ModelVersionInfo) {
  if (model.model_type === "baseline") return "RuleBased Baseline";
  if (model.model_type === "logistic_regression") return "Logistic Regression";
  if (model.model_type === "hist_gradient_boosting_classifier") {
    return "HistGradientBoosting Classifier";
  }
  if (model.model_type === "random_forest_classifier") return "Random Forest";
  if (model.model_type === "dynamic_regime_ensemble") return "Regime Ensemble";
  return "HistGradientBoosting Return";
}

function statusLabel(status: ModelVersionInfo["status"]) {
  const labels: Record<ModelVersionInfo["status"], string> = {
    baseline: "기준 모델",
    candidate: "후보",
    active: "운영 중",
    rejected: "검증 미달",
    archived: "보관",
  };
  return labels[status];
}

function dateRange(start?: string | null, end?: string | null) {
  if (!start || !end) return "-";
  return `${start} ~ ${end}`;
}

function formatMetric(value: number | null | undefined, suffix: string) {
  if (value === null || value === undefined) return "-";
  return `${value.toFixed(suffix === "%" || suffix === "%p" ? 2 : 4)}${suffix}`;
}
