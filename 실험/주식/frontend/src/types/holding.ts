export interface Holding {
  id: number;
  stock_id: number;
  name: string;
  ticker: string;
  market_type: "KR" | "US" | "PRIVATE" | "OTHER";
  asset_type: "LISTED_STOCK" | "PRIVATE" | "ETF" | "OTHER";
  avg_buy_price: number;
  quantity: number;
  currency: string;
  investment_memo: string | null;
  interest_level: number;
  risk_tolerance: "low" | "medium" | "high";
  is_active: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export type HoldingInput = Omit<
  Holding,
  "id" | "stock_id" | "currency" | "is_active" | "created_at" | "updated_at"
> & { currency?: string };
