export interface AnalysisJob {
  id: number;
  status: "queued" | "running" | "completed" | "cancelled" | "failed";
  market: string;
  total_items: number;
  completed_items: number;
  failed_items: number;
  processed_items: number;
  progress_percent: number;
  current_ticker: string | null;
  message: string;
  errors: Array<{ ticker: string; error: string }>;
  cancel_requested: boolean;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface BacktestSummary {
  evaluated: number;
  direction_evaluated: number;
  correct: number;
  accuracy: number | null;
  mean_absolute_error: number | null;
  range_accuracy: number | null;
  recent_3m_accuracy: number | null;
  recent_2y_accuracy: number | null;
  status: "ready" | "collecting";
  calibration_status: "insufficient" | "reference_available" | "high_sample_review";
  minimum_recommended_samples: number;
  high_confidence_review_samples: number;
  methodology: "historical_replay";
  candidate_model: {
    status: "insufficient" | "candidate" | "not_improved";
    message: string;
    name?: string;
    weights?: Record<string, number>;
    training_accuracy?: number | null;
    baseline_validation_accuracy?: number | null;
    candidate_validation_accuracy?: number | null;
    training_samples: number;
    validation_samples: number;
    applied: false;
    component_performance: Record<string, number | null>;
  };
  details: Array<{
    ticker: string;
    name: string;
    market: string;
    prediction_date: string;
    target_date: string | null;
    up_probability: number;
    calibrated_up_probability: number;
    expected_range_low: number;
    expected_range_high: number;
    actual_return: number | null;
    actual_direction: "up" | "down" | "flat" | null;
    is_correct: boolean | null;
    range_hit: boolean | null;
    absolute_error: number | null;
    horizon_days: number;
    data_quality_note: string;
    historical_news_available: boolean;
    historical_financial_available: boolean;
  }>;
}

export interface HistoricalReplayRun {
  id: number;
  start_date: string;
  end_date: string;
  market_scope: string[];
  stock_scope: string;
  horizon_days: number;
  status: "queued" | "running" | "completed" | "failed";
  stage: "queued" | "loading_prices" | "replaying" | "completed" | "failed";
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  processed_tasks: number;
  current_ticker: string | null;
  current_date: string | null;
  progress_percent: number;
  errors: Array<{ ticker?: string; date?: string; error: string }>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface SchedulerState {
  running: boolean;
  enabled: boolean;
  next_run_time: string | null;
  timezone: string;
  analysis?: {
    enabled: boolean;
    next_run_time: string | null;
  };
  prediction_validation?: {
    enabled: boolean;
    next_run_time: string | null;
    timezone: string;
  };
}

export interface DailyValidationRefreshResult {
  success: boolean;
  created: boolean;
  reason: "started" | "already_running" | "already_refreshed_today";
  run: HistoricalReplayRun;
}

export interface MlMetricSummary {
  samples?: number;
  accuracy?: number;
  precision_up?: number;
  precision_down?: number;
  recall_up?: number;
  recall_down?: number;
  f1?: number;
  f1_macro?: number;
  roc_auc?: number | null;
  pr_auc?: number | null;
  brier_score?: number;
  log_loss?: number;
  expected_calibration_error?: number;
  mean_absolute_error?: number;
  baseline_mean_absolute_error?: number;
  positive_rate?: number;
  confidence_threshold?: number;
  meaningful_move?: {
    samples: number;
    accuracy: number | null;
    minimum_move_percent?: number;
  };
  high_confidence?: {
    threshold: number;
    trades: number;
    signal_frequency: number;
    accuracy: number | null;
    average_net_return: number | null;
    cumulative_net_return: number | null;
    maximum_drawdown: number | null;
    sharpe: number | null;
    sortino: number | null;
  };
  candidate_criteria?: {
    eligible: boolean;
    mode?: "broad_direction" | "selective_high_confidence" | null;
    reasons: string[];
    automatic_activation: boolean;
  } | null;
  baseline?: MlMetricSummary | null;
  walk_forward?: {
    month_count: number;
    accuracy_std: number | null;
    worst_accuracy: number | null;
    stable: boolean;
    months: Array<Record<string, number | string | null>>;
  } | null;
}

export interface ModelVersionInfo {
  id: number;
  version_name: string;
  model_type:
    | "baseline"
    | "logistic_regression"
    | "hist_gradient_boosting_classifier"
    | "random_forest_classifier"
    | "dynamic_regime_ensemble"
    | "hist_gradient_boosting_regressor";
  status: "baseline" | "candidate" | "active" | "rejected" | "archived";
  is_active: boolean;
  recommended: boolean;
  feature_schema: string[];
  training_summary: MlMetricSummary;
  validation_summary: MlMetricSummary;
  test_summary: MlMetricSummary;
  artifact_path: string;
  metadata_path: string;
  created_at: string;
  can_activate: boolean;
}

export interface ModelExperimentInfo {
  id: number;
  experiment_name: string;
  model_type: string;
  feature_set_version: string;
  train_start_date: string | null;
  train_end_date: string | null;
  calibration_start_date: string | null;
  calibration_end_date: string | null;
  test_start_date: string | null;
  test_end_date: string | null;
  parameters: Record<string, unknown>;
  metrics: Record<string, unknown>;
  status: string;
  created_at: string;
}

export interface ModelOverview {
  active_model: ModelVersionInfo;
  baseline_version: string;
  models: ModelVersionInfo[];
  experiments: ModelExperimentInfo[];
  activation_history: Array<{
    id: number;
    from_version: string | null;
    to_version: string;
    action: string;
    reason: string;
    created_at: string;
  }>;
}

export interface SegmentMetric {
  segment: string;
  samples: number;
  accuracy: number;
  mean_probability: number;
  observed_up_rate: number;
}

export interface PerformanceDiagnostics {
  status: "ready" | "insufficient";
  as_of_date?: string;
  methodology: {
    prediction_timing: string;
    target: string;
    intraday_prices_used: boolean;
    market_regime_basis: string;
    flat_handling: string;
    all_sample_count: number;
    direction_sample_count: number;
    flat_excluded: number;
    invalid_snapshot_excluded: number;
    return_curve_note: string;
  };
  overall: MlMetricSummary & {
    meaningful_move?: { samples: number; accuracy: number | null };
  };
  periods: Array<{
    period: string;
    samples: number;
    accuracy: number | null;
    brier_score?: number;
    expected_calibration_error?: number;
  }>;
  segments: {
    market: SegmentMetric[];
    market_regime: SegmentMetric[];
    volatility: SegmentMetric[];
    liquidity: SegmentMetric[];
    stocks_best: SegmentMetric[];
    stocks_worst: SegmentMetric[];
  };
  selective_signal: {
    threshold?: number;
    trades?: number;
    signal_frequency?: number;
    accuracy?: number | null;
    average_net_return?: number | null;
    cumulative_net_return?: number | null;
    maximum_drawdown?: number | null;
    sharpe?: number | null;
    sortino?: number | null;
    transaction_cost_percent?: number;
  };
  data_quality: Record<string, unknown>;
  leakage_audit: Array<{
    item: string;
    status: "pass" | "limited";
    evidence: string;
  }>;
  available_features?: Record<string, boolean>;
}

export interface ResearchSummary {
  principles: string[];
  references: Array<{
    title: string;
    author: string;
    date: string;
    url: string;
    method: string;
    application: string;
    limitation: string;
  }>;
}

export interface MlTrainingResult {
  status: "completed" | "insufficient";
  message: string;
  recommended_version?: string | null;
  counts: {
    training: number;
    calibration: number;
    test: number;
  };
  feature_columns?: string[];
  baseline_test?: MlMetricSummary;
  trained_models?: Array<{
    version_name: string;
    model_type: string;
    status: string;
    metrics: Record<string, unknown>;
  }>;
  overview: ModelOverview;
}

export interface PortfolioSummary {
  currency_summaries: Array<{
    currency: string;
    total_cost: number;
    total_value: number;
    total_pnl: number;
    total_pnl_rate: number | null;
  }>;
  mixed_currencies: boolean;
  largest_position_weight: number;
  concentration_warning: boolean;
  positions: Array<{
    holding_id: number;
    ticker: string;
    name: string;
    market: string;
    currency: string;
    quantity: number;
    avg_buy_price: number;
    current_price: number | null;
    cost: number;
    value: number | null;
    pnl: number | null;
    pnl_rate: number | null;
    weight: number;
    risk_tolerance: string;
  }>;
}

export interface AllocationPlan {
  capital: number;
  currency: "KRW" | "USD";
  risk_profile: "low" | "medium" | "high";
  invested_amount: number;
  cash_reserve: number;
  cash_reserve_rate: number;
  expected_2d_return: number;
  expected_profit: number;
  downside_scenario_return: number;
  downside_scenario_amount: number;
  estimated_annual_volatility: number;
  generated_from_reports: number;
  methodology: string[];
  warnings: string[];
  allocations: Array<{
    ticker: string;
    name: string;
    market: string;
    currency: string;
    current_price: number;
    quantity: number;
    amount: number;
    weight: number;
    up_probability: number;
    expected_2d_return: number;
    downside_scenario_return: number;
    data_quality_score: number;
    final_score: number;
    annual_volatility: number;
    surge_warning: boolean;
    reason: string;
  }>;
}
