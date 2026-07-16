export interface Recommendation {
  id: number;
  report_date: string;
  rank: number;
  stock_id: number;
  ticker: string;
  name: string;
  market: string;
  total_score: number;
  up_probability: number;
  expected_range_low: number;
  expected_range_high: number;
  reason: string;
  risk_summary: string;
  time_horizon: string;
  checklist: string;
  surge_warning: boolean;
  surge_reason: string;
}
