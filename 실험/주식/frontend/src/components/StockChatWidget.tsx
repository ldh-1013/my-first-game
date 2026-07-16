import {
  Bot,
  ChevronDown,
  ExternalLink,
  MessageCircle,
  Send,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import type {
  ChatMessage,
  StockChatResponse,
  StockChatStatus,
} from "../types/chat";

const STARTERS = [
  "삼성전자는 오늘 왜 떨어졌어?",
  "NVDA 관련 뉴스와 차트를 함께 분석해줘",
  "애플 지금 매수해도 될까?",
];

interface StockChatWidgetProps {
  contextTicker?: string;
  onOpenStock?: (ticker: string) => void;
}

export default function StockChatWidget({
  contextTicker,
  onOpenStock,
}: StockChatWidgetProps) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<StockChatStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    stockApi.chatStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    if (!open) return;
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading, open]);

  const assistantHistory = useMemo(
    () =>
      messages.slice(-8).map((message) => ({
        role: message.role,
        content:
          message.role === "assistant"
            ? message.response?.answer ?? message.content
            : message.content,
      })),
    [messages],
  );

  const ask = async (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setLoading(true);
    setError("");
    try {
      const response = await stockApi.askStockChat({
        question: trimmed,
        ticker: contextTicker || undefined,
        history: assistantHistory,
      });
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          response,
        },
      ]);
    } catch (askError) {
      setError(getApiError(askError));
    } finally {
      setLoading(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void ask(question);
  };

  return (
    <div className={`stock-chat ${open ? "open" : ""}`}>
      {open && (
        <section className="stock-chat-window" aria-label="주식 근거 분석 챗봇">
          <header>
            <div className="stock-chat-brand">
              <span>
                <Bot size={19} />
              </span>
              <div>
                <strong>Insight AI</strong>
                <small>
                  {status?.mode === "openai_grounded"
                    ? `AI 강화 · ${status.model}`
                    : "근거 우선 분석"}
                </small>
              </div>
            </div>
            <div className="stock-chat-header-actions">
              {messages.length > 0 && (
                <button
                  type="button"
                  aria-label="대화 내용 지우기"
                  onClick={() => setMessages([])}
                >
                  <Trash2 size={15} />
                </button>
              )}
              <button
                type="button"
                aria-label="챗봇 닫기"
                onClick={() => setOpen(false)}
              >
                <X size={17} />
              </button>
            </div>
          </header>

          <div className="stock-chat-context">
            <ShieldCheck size={14} />
            <span>
              가격·뉴스·공시·차트 근거만 사용
              {contextTicker ? ` · 현재 종목 ${contextTicker}` : ""}
            </span>
          </div>

          <div className="stock-chat-messages" ref={scrollRef}>
            {!messages.length && (
              <div className="stock-chat-welcome">
                <span className="stock-chat-bot-icon">
                  <Bot size={21} />
                </span>
                <strong>어떤 종목이 궁금하세요?</strong>
                <p>
                  하락 이유, 관련 뉴스, 차트 상태, 매수·매도 참고 신호를
                  저장된 근거와 함께 설명합니다.
                </p>
                <div className="stock-chat-starters">
                  {STARTERS.map((starter) => (
                    <button type="button" key={starter} onClick={() => void ask(starter)}>
                      {starter}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) =>
              message.role === "user" ? (
                <div className="stock-chat-user" key={message.id}>
                  {message.content}
                </div>
              ) : (
                <AssistantMessage
                  key={message.id}
                  response={message.response}
                  onOpenStock={onOpenStock}
                  onFollowup={(value) => void ask(value)}
                />
              ),
            )}

            {loading && (
              <div className="stock-chat-loading">
                <span />
                <span />
                <span />
                근거를 비교하고 있습니다
              </div>
            )}
            {error && <div className="stock-chat-error">{error}</div>}
          </div>

          <form onSubmit={submit} className="stock-chat-input">
            <textarea
              value={question}
              rows={1}
              placeholder="예: 삼성전자는 왜 떨어졌어?"
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  if (question.trim()) void ask(question);
                }
              }}
            />
            <button type="submit" disabled={!question.trim() || loading} aria-label="질문 보내기">
              <Send size={17} />
            </button>
          </form>
          <footer>
            공식 공시가 없는 원인은 가능성으로 설명하며 수익을 보장하지 않습니다.
          </footer>
        </section>
      )}

      <button
        className="stock-chat-trigger"
        type="button"
        aria-label={open ? "챗봇 닫기" : "AI 주식 분석 챗봇 열기"}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? <X size={22} /> : <MessageCircle size={23} />}
        {!open && <span>AI에게 물어보기</span>}
      </button>
    </div>
  );
}

function AssistantMessage({
  response,
  onOpenStock,
  onFollowup,
}: {
  response?: StockChatResponse;
  onOpenStock?: (ticker: string) => void;
  onFollowup: (question: string) => void;
}) {
  if (!response) return null;
  const cited = new Set(response.cited_evidence_ids);
  const citedEvidence = response.evidence.filter((row) => cited.has(row.id));
  return (
    <article className="stock-chat-assistant">
      <div className="stock-chat-answer-head">
        <span className="stock-chat-bot-icon">
          <Bot size={17} />
        </span>
        <div>
          <strong>{response.headline}</strong>
          <small>
            {confidenceLabel(response.confidence)}
            {response.as_of ? ` · ${response.as_of} 기준` : ""}
          </small>
        </div>
      </div>
      {response.stock && (
        <button
          type="button"
          className="stock-chat-stock-link"
          onClick={() => onOpenStock?.(response.stock!.ticker)}
        >
          {response.stock.name} · {response.stock.ticker}
        </button>
      )}
      <p className="stock-chat-answer">{response.answer}</p>

      {citedEvidence.length > 0 && (
        <details className="stock-chat-sources">
          <summary>
            근거 {citedEvidence.length}개 보기 <ChevronDown size={14} />
          </summary>
          <div>
            {citedEvidence.map((evidence) => (
              <EvidenceRow evidence={evidence} key={evidence.id} />
            ))}
          </div>
        </details>
      )}

      <p className="stock-chat-notice">{response.notice}</p>
      {response.followups.length > 0 && (
        <div className="stock-chat-followups">
          {response.followups.map((followup) => (
            <button type="button" key={followup} onClick={() => onFollowup(followup)}>
              {followup}
            </button>
          ))}
        </div>
      )}
    </article>
  );
}

function EvidenceRow({ evidence }: { evidence: StockChatResponse["evidence"][number] }) {
  const content = (
    <>
      <span className={`stock-chat-source-type ${evidence.strength}`}>
        {sourceTypeLabel(evidence.category)}
      </span>
      <div>
        <strong>
          [{evidence.id}] {evidence.title}
        </strong>
        <p>{evidence.detail}</p>
        <small>
          {evidence.source_label}
          {evidence.observed_at ? ` · ${formatDate(evidence.observed_at)}` : ""}
        </small>
      </div>
      {evidence.url && <ExternalLink size={14} />}
    </>
  );
  return evidence.url ? (
    <a href={evidence.url} target="_blank" rel="noreferrer">
      {content}
    </a>
  ) : (
    <div>{content}</div>
  );
}

function confidenceLabel(value: StockChatResponse["confidence"]) {
  if (value === "high") return "근거 신뢰도 높음";
  if (value === "medium") return "근거 신뢰도 보통";
  return "근거 제한적";
}

function sourceTypeLabel(value: StockChatResponse["evidence"][number]["category"]) {
  const labels = {
    price: "가격",
    market: "시장",
    technical: "차트",
    news: "뉴스",
    report: "리포트",
    financial: "재무",
  };
  return labels[value];
}

function formatDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString("ko-KR");
}
