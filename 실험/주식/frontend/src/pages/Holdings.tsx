import { Pencil, Plus, Search, Star, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import type { Holding, HoldingInput } from "../types/holding";

const initialForm: HoldingInput = {
  ticker: "",
  name: "",
  market_type: "US",
  asset_type: "LISTED_STOCK",
  avg_buy_price: 0,
  quantity: 0,
  investment_memo: "",
  interest_level: 3,
  risk_tolerance: "medium",
  tags: [],
};

export default function Holdings() {
  const [rows, setRows] = useState<Holding[]>([]);
  const [form, setForm] = useState<HoldingInput>(initialForm);
  const [tagText, setTagText] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const load = () => stockApi.holdings().then(setRows).catch((err) => setError(getApiError(err)));
  useEffect(() => void load(), []);
  const filtered = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return rows;
    return rows.filter(
      (row) =>
        row.name.toLowerCase().includes(value) ||
        row.ticker.toLowerCase().includes(value) ||
        row.tags.some((tag) => tag.toLowerCase().includes(value)),
    );
  }, [query, rows]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    const payload = {
      ...form,
      tags: tagText.split(",").map((tag) => tag.trim()).filter(Boolean),
    };
    try {
      if (editingId !== null) {
        const { ticker: _ticker, ...updates } = payload;
        await stockApi.updateHolding(editingId, updates);
      } else {
        await stockApi.addHolding(payload);
      }
      close();
      await load();
    } catch (err) {
      setError(getApiError(err));
    }
  };
  const close = () => {
    setForm(initialForm);
    setTagText("");
    setEditingId(null);
    setShowForm(false);
  };
  const edit = (row: Holding) => {
    setForm({
      ticker: row.ticker,
      name: row.name,
      market_type: row.market_type,
      asset_type: row.asset_type,
      avg_buy_price: row.avg_buy_price,
      quantity: row.quantity,
      investment_memo: row.investment_memo,
      interest_level: row.interest_level,
      risk_tolerance: row.risk_tolerance,
      tags: row.tags,
    });
    setTagText(row.tags.join(", "));
    setEditingId(row.id);
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">WATCHLIST & HOLDINGS</p>
          <h1>보유·관심 종목</h1>
          <p>태그와 메모로 종목을 분류하고 검색할 수 있습니다.</p>
        </div>
        <button className="primary-button" onClick={() => (showForm ? close() : setShowForm(true))}>
          <Plus size={18} /> 종목 추가
        </button>
      </header>
      {error && <div className="error-message">{error}</div>}
      <label className="search-box">
        <Search size={17} />
        <input value={query} placeholder="종목명·티커·태그 검색" onChange={(event) => setQuery(event.target.value)} />
      </label>
      {showForm && (
        <form className="holding-form" onSubmit={submit}>
          <Field label="종목 코드"><input required disabled={editingId !== null} value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} /></Field>
          <Field label="종목명"><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="시장"><select value={form.market_type} onChange={(e) => setForm({ ...form, market_type: e.target.value as HoldingInput["market_type"] })}><option value="KR">한국</option><option value="US">미국</option><option value="PRIVATE">비상장</option><option value="OTHER">기타</option></select></Field>
          <Field label="자산 유형"><select value={form.asset_type} onChange={(e) => setForm({ ...form, asset_type: e.target.value as HoldingInput["asset_type"] })}><option value="LISTED_STOCK">상장 주식</option><option value="ETF">ETF</option><option value="PRIVATE">비상장</option><option value="OTHER">기타</option></select></Field>
          <Field label="평균 매수가"><input min="0" step="any" type="number" value={form.avg_buy_price} onChange={(e) => setForm({ ...form, avg_buy_price: Number(e.target.value) })} /></Field>
          <Field label="수량"><input min="0" step="any" type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} /></Field>
          <Field label="관심도"><select value={form.interest_level} onChange={(e) => setForm({ ...form, interest_level: Number(e.target.value) })}>{[1,2,3,4,5].map((value) => <option key={value}>{value}</option>)}</select></Field>
          <Field label="위험 허용도"><select value={form.risk_tolerance} onChange={(e) => setForm({ ...form, risk_tolerance: e.target.value as HoldingInput["risk_tolerance"] })}><option value="low">낮음</option><option value="medium">중간</option><option value="high">높음</option></select></Field>
          <Field label="태그(쉼표 구분)"><input value={tagText} placeholder="반도체, 장기, 배당" onChange={(e) => setTagText(e.target.value)} /></Field>
          <label className="full">투자 메모<textarea value={form.investment_memo ?? ""} onChange={(e) => setForm({ ...form, investment_memo: e.target.value })} /></label>
          <div className="form-actions full"><button type="button" className="ghost-button" onClick={close}>취소</button><button className="primary-button">저장</button></div>
        </form>
      )}
      <div className="holding-list">
        {filtered.map((row) => (
          <article key={row.id}>
            <div className="holding-symbol">{row.ticker.slice(0, 2)}</div>
            <div className="holding-main">
              <p className="eyebrow">{row.market_type} · {row.ticker}</p>
              <h3>{row.name}</h3>
              <p>{row.investment_memo || "등록된 메모 없음"}</p>
              <div className="tag-list">{row.tags.map((tag) => <span key={tag}>#{tag}</span>)}</div>
            </div>
            <div className="holding-data"><span>평균가</span><strong>{row.avg_buy_price.toLocaleString()} {row.currency}</strong></div>
            <div className="holding-data"><span>수량</span><strong>{row.quantity.toLocaleString()}</strong></div>
            <div className="interest"><Star size={16} fill="currentColor" />{row.interest_level}</div>
            <button className="icon-button" onClick={() => edit(row)}><Pencil size={17} /></button>
            <button className="icon-button danger" onClick={async () => { if (window.confirm("이 종목을 목록에서 비활성화할까요?")) { await stockApi.deleteHolding(row.id); await load(); } }}><Trash2 size={17} /></button>
          </article>
        ))}
        {!filtered.length && <div className="empty-state large">검색 결과가 없습니다.</div>}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label>{label}{children}</label>;
}
