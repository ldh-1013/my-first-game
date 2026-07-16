export interface ChatEvidence {
  id: string;
  category: "price" | "market" | "technical" | "news" | "report" | "financial";
  title: string;
  detail: string;
  source_label: string;
  url: string | null;
  observed_at: string | null;
  strength: "fact" | "context" | "hypothesis";
}

export interface StockChatResponse {
  mode: "local_evidence" | "openai_grounded";
  model: string | null;
  stock: {
    ticker: string;
    name: string;
    market: string;
  } | null;
  question_type: string;
  headline: string;
  answer: string;
  confidence: "high" | "medium" | "low";
  as_of: string | null;
  evidence: ChatEvidence[];
  cited_evidence_ids: string[];
  followups: string[];
  notice: string;
}

export interface StockChatStatus {
  available: boolean;
  mode: "local_evidence" | "openai_grounded";
  model: string | null;
  description: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: StockChatResponse;
}
