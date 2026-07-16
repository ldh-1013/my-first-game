import { DatabaseBackup, RefreshCw, Save, Send, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { getApiError, stockApi } from "../api/client";
import type { SchedulerState } from "../types/analytics";

const defaultWeights = {
  news: 25,
  technical: 25,
  volume: 20,
  financial: 20,
  industry_macro: 10,
  risk_penalty: 8,
};

export default function Settings() {
  const [values, setValues] = useState<Record<string, string>>({
    collection_time: "08:30",
    default_market: "ALL",
    schedule_enabled: "false",
    validation_schedule_enabled: "true",
    validation_time: "18:10",
    dart_api_key: "",
    discord_webhook_url: "",
    telegram_bot_token: "",
    telegram_chat_id: "",
    alert_gain_percent: "10",
    alert_loss_percent: "-8",
  });
  const [weights, setWeights] = useState(defaultWeights);
  const [backups, setBackups] = useState<Array<{ filename: string; size: number; modified_at: string }>>([]);
  const [scheduler, setScheduler] = useState<SchedulerState | null>(null);
  const [message, setMessage] = useState("");

  const load = async () => {
    const [settings, backupRows, schedulerState] = await Promise.all([
      stockApi.settings(),
      stockApi.backups(),
      stockApi.scheduler(),
    ]);
    const map = Object.fromEntries(settings.map((row) => [row.key, row.value]));
    setValues((current) => ({ ...current, ...map }));
    if (map.scoring_weights) {
      try {
        const parsed = JSON.parse(map.scoring_weights) as Record<string, number>;
        setWeights({
          news: Math.round((parsed.news ?? 0.25) * 100),
          technical: Math.round((parsed.technical ?? 0.25) * 100),
          volume: Math.round((parsed.volume ?? 0.2) * 100),
          financial: Math.round((parsed.financial ?? 0.2) * 100),
          industry_macro: Math.round((parsed.industry_macro ?? 0.1) * 100),
          risk_penalty: Math.round((parsed.risk_penalty ?? 0.08) * 100),
        });
      } catch {
        setWeights(defaultWeights);
      }
    }
    setBackups(backupRows);
    setScheduler(schedulerState);
  };
  useEffect(() => {
    load().catch((err) => setMessage(getApiError(err)));
  }, []);

  const setValue = (key: string, value: string) => setValues((current) => ({ ...current, [key]: value }));
  const save = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const weightPayload = Object.fromEntries(
        Object.entries(weights).map(([key, value]) => [key, value / 100]),
      );
      await Promise.all([
        ...Object.entries(values).map(([key, value]) => stockApi.saveSetting(key, value)),
        stockApi.saveSetting("scoring_weights", JSON.stringify(weightPayload)),
      ]);
      await stockApi.reloadScheduler();
      setMessage("설정을 저장하고 자동 분석 일정을 갱신했습니다.");
      await load();
    } catch (err) {
      setMessage(getApiError(err));
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">AUTOMATION & DATA</p>
          <h1>자동화·설정</h1>
          <p>실제로 분석 계산에 적용되는 가중치, 예약 실행, 알림, DART와 백업을 관리합니다.</p>
        </div>
      </header>
      {message && <div className="status-message">{message}</div>}
      <form className="settings-stack" onSubmit={save}>
        <section className="settings-form panel">
          <div><h3>예약 분석</h3><p>프로그램이 실행 중일 때 지정 시각에 백그라운드 분석을 시작합니다.</p></div>
          <label>자동 분석<select value={values.schedule_enabled} onChange={(e) => setValue("schedule_enabled", e.target.value)}><option value="false">사용 안 함</option><option value="true">사용</option></select></label>
          <label>실행 시각<input type="time" value={values.collection_time} onChange={(e) => setValue("collection_time", e.target.value)} /></label>
          <label>기본 시장<select value={values.default_market} onChange={(e) => setValue("default_market", e.target.value)}><option value="ALL">전체</option><option value="KR">한국</option><option value="US">미국</option></select></label>
          <small>다음 실행: {scheduler?.next_run_time ? new Date(scheduler.next_run_time).toLocaleString("ko-KR") : "예약 없음"}</small>
          <label>예측 검증 자동 최신화<select value={values.validation_schedule_enabled} onChange={(e) => setValue("validation_schedule_enabled", e.target.value)}><option value="true">사용</option><option value="false">사용 안 함</option></select></label>
          <label>예측 검증 실행 시각<input type="time" value={values.validation_time} onChange={(e) => setValue("validation_time", e.target.value)} /></label>
          <small>다음 예측 검증: {scheduler?.prediction_validation?.next_run_time ? new Date(scheduler.prediction_validation.next_run_time).toLocaleString("ko-KR") : "예약 없음"}</small>
        </section>

        <section className="settings-form panel">
          <div><h3>분석 가중치</h3><p>재무 데이터가 없는 종목은 데이터 품질 점수가 낮아지고 판단 보류될 수 있습니다.</p></div>
          {Object.entries(weights).map(([key, value]) => (
            <label key={key}>{weightLabel(key)} <input type="number" min="0" max="100" value={value} onChange={(e) => setWeights((current) => ({ ...current, [key]: Number(e.target.value) }))} /></label>
          ))}
        </section>

        <section className="settings-form panel">
          <div><h3>DART·알림 연결</h3><p>키와 웹훅은 이 PC의 로컬 DB에만 저장됩니다. SEC 조회는 별도 키가 필요 없습니다.</p></div>
          <label>DART API 키<input type="password" value={values.dart_api_key} onChange={(e) => setValue("dart_api_key", e.target.value)} /></label>
          <label>디스코드 웹훅<input value={values.discord_webhook_url} onChange={(e) => setValue("discord_webhook_url", e.target.value)} /></label>
          <label>텔레그램 봇 토큰<input type="password" value={values.telegram_bot_token} onChange={(e) => setValue("telegram_bot_token", e.target.value)} /></label>
          <label>텔레그램 채팅 ID<input value={values.telegram_chat_id} onChange={(e) => setValue("telegram_chat_id", e.target.value)} /></label>
          <label>목표 수익률 알림(%)<input type="number" value={values.alert_gain_percent} onChange={(e) => setValue("alert_gain_percent", e.target.value)} /></label>
          <label>손실 알림(%)<input type="number" value={values.alert_loss_percent} onChange={(e) => setValue("alert_loss_percent", e.target.value)} /></label>
          <button type="button" className="ghost-button" onClick={async () => { const result = await stockApi.checkAlerts() as { created: number }; setMessage(`알림 점검 완료 · 새 알림 ${result.created}건`); }}><Send size={16} /> 지금 알림 점검</button>
        </section>

        <div className="form-actions sticky-actions">
          <button className="primary-button" type="submit"><Save size={16} /> 전체 설정 저장</button>
        </div>
      </form>

      <section className="panel">
        <div className="section-heading">
          <div><p className="eyebrow">LOCAL DATABASE</p><h2>백업·복원·정리</h2></div>
          <div className="inline-actions">
            <button className="ghost-button" onClick={async () => { await stockApi.createBackup(); setMessage("DB 백업을 생성했습니다."); await load(); }}><DatabaseBackup size={16} /> 백업 생성</button>
            <button className="ghost-button" onClick={async () => { await stockApi.cleanup(); setMessage("2년 이전 데이터를 정리했습니다."); }}><Trash2 size={16} /> 오래된 데이터 정리</button>
          </div>
        </div>
        <div className="backup-list">
          {backups.map((row) => (
            <div key={row.filename}>
              <span><strong>{row.filename}</strong><small>{(row.size / 1024 / 1024).toFixed(1)} MB · {new Date(row.modified_at).toLocaleString("ko-KR")}</small></span>
              <button className="ghost-button" onClick={async () => { if (window.confirm("선택한 백업으로 복원할까요? 현재 DB는 자동으로 긴급 백업됩니다.")) { await stockApi.restoreBackup(row.filename); setMessage("복원 완료. 앱을 다시 실행해 주세요."); } }}><RefreshCw size={15} /> 복원</button>
            </div>
          ))}
          {!backups.length && <div className="empty-state">생성된 백업이 없습니다.</div>}
        </div>
      </section>
    </div>
  );
}

function weightLabel(key: string) {
  return ({ news: "뉴스", technical: "기술적 지표", volume: "거래량", financial: "재무", industry_macro: "산업·거시", risk_penalty: "위험 감점" } as Record<string, string>)[key] ?? key;
}
