export interface PricePoint {
  date: string;
  open_price: number | null;
  high_price: number | null;
  low_price: number | null;
  close_price: number | null;
  volume: number | null;
  change_rate: number | null;
  ma5: number | null;
  ma20: number | null;
  ma60: number | null;
  rsi: number | null;
  atr: number | null;
  volatility_20d: number | null;
  volume_change_rate: number | null;
}

export interface IntradayPoint {
  timestamp: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number | null;
}

export interface IntradayResponse {
  ticker: string;
  resolved_ticker: string;
  interval: string;
  refresh_seconds: number;
  fetched_at: string;
  latest_timestamp: string | null;
  latest_price: number | null;
  change_rate: number | null;
  market_state: "receiving" | "open" | "closed" | "no_data";
  market_state_label: string;
  delay_minutes: number | null;
  timezone: string;
  delay_notice: string;
  points: IntradayPoint[];
}

export interface NewsArticle {
  id: number;
  title: string;
  summary: string | null;
  translated_title: string | null;
  translated_summary: string | null;
  source: string | null;
  url: string;
  published_at: string | null;
  language: string;
  is_official: boolean;
  is_rumor: boolean;
  sentiment_label: "positive" | "neutral" | "negative" | null;
  sentiment_score: number | null;
}

export interface StockResearch {
  ticker: string;
  name: string;
  financial: null | {
    as_of_date: string;
    revenue: number | null;
    operating_income: number | null;
    net_income: number | null;
    total_debt: number | null;
    free_cash_flow: number | null;
    market_cap: number | null;
    trailing_pe: number | null;
    price_to_book: number | null;
    return_on_equity: number | null;
    earnings_growth: number | null;
    source: string;
    summary: string;
  };
  disclosures: Array<{
    source: string;
    title: string;
    date: string;
    url: string;
    company: string;
  }>;
  disclosure_source: "DART" | "SEC";
  configuration_required: boolean;
}
