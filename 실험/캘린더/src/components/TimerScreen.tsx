import { AlarmClock, BellRing, Pause, Play, RotateCcw } from 'lucide-react';
import { Fragment, useEffect, useState } from 'react';
import { useAnimationTick } from '../store/ticker';
import { timerRemaining, useToolStore } from '../store/toolStore';
import { formatCountdown } from '../utils/duration';
import { ensureAudio } from '../utils/sound';
import { ToolScreen } from './ToolScreen';
import styles from './TimerScreen.module.css';

// StatsWidget의 도넛과 같은 지오메트리: 둘레가 정확히 100이 되는 반지름
const RADIUS = 15.9155;
const STROKE = 2.2;

const PRESETS: { label: string; ms: number }[] = [
  { label: '1분', ms: 60_000 },
  { label: '3분', ms: 3 * 60_000 },
  { label: '5분', ms: 5 * 60_000 },
  { label: '10분', ms: 10 * 60_000 },
  { label: '25분', ms: 25 * 60_000 },
  { label: '45분', ms: 45 * 60_000 },
  { label: '1시간', ms: 60 * 60_000 },
];

const MAX_HOURS = 99;

const FIELD_DEFS: { key: 'h' | 'm' | 's'; label: string }[] = [
  { key: 'h', label: '시간' },
  { key: 'm', label: '분' },
  { key: 's', label: '초' },
];

/** 숫자만 남기고 두 자리로 제한 — 입력 중에도 값이 튀지 않게 문자열 단계에서 정리한다 */
function sanitize(value: string): string {
  return value.replace(/\D/g, '').slice(0, 2);
}

/** 설정값(ms)을 시/분/초 입력창에 넣을 문자열로 쪼갠다 */
function toFields(ms: number): { h: string; m: string; s: string } {
  const totalSeconds = Math.floor(ms / 1000);
  return {
    h: String(Math.floor(totalSeconds / 3600)),
    m: String(Math.floor(totalSeconds / 60) % 60),
    s: String(totalSeconds % 60),
  };
}

export function TimerScreen() {
  const screen = useToolStore((s) => s.screen);
  const timer = useToolStore((s) => s.timer);
  const setTimerDuration = useToolStore((s) => s.setTimerDuration);
  const toggleTimer = useToolStore((s) => s.toggleTimer);
  const resetTimer = useToolStore((s) => s.resetTimer);
  const dismissTimerAlert = useToolStore((s) => s.dismissTimerAlert);

  // 스톱워치와 같은 이유로, 보이면서 흐를 때만 매 프레임 갱신한다
  useAnimationTick(screen === 'timer' && timer.running);

  const remaining = timerRemaining(timer);
  const countdown = formatCountdown(remaining);
  const progress = timer.durationMs > 0 ? remaining / timer.durationMs : 0;
  const dash = Math.min(Math.max(progress * 100, 0), 100);

  // 입력창은 타이핑 도중의 '' 나 '05' 같은 중간 상태를 그대로 두어야 해서 로컬 문자열로 관리한다.
  const [fields, setFields] = useState(() => toFields(timer.durationMs));

  // 프리셋처럼 바깥에서 설정값이 바뀐 경우에만 입력창을 다시 맞춘다.
  // 로컬 값이 이미 같은 시간을 가리키면 건드리지 않아, 타이핑 중 커서가 튀지 않는다.
  useEffect(() => {
    const localMs =
      (Number(fields.h) || 0) * 3_600_000 +
      (Number(fields.m) || 0) * 60_000 +
      (Number(fields.s) || 0) * 1000;
    if (localMs === timer.durationMs) return;
    setFields(toFields(timer.durationMs));
    // 설정값이 바뀐 순간에만 반응해야 하므로 입력 상태(fields)는 의존성에서 뺀다
  }, [timer.durationMs]);

  /** 한 칸을 고치면 세 칸을 합쳐 설정값으로 반영한다. 분·초는 60 이상이면 잘라낸다. */
  const handleField = (key: 'h' | 'm' | 's', raw: string) => {
    const next = { ...fields, [key]: sanitize(raw) };
    setFields(next);
    const h = Math.min(Number(next.h) || 0, MAX_HOURS);
    const m = Math.min(Number(next.m) || 0, 59);
    const s = Math.min(Number(next.s) || 0, 59);
    setTimerDuration(h * 3_600_000 + m * 60_000 + s * 1000);
  };

  const handleToggle = () => {
    // 자동재생 정책에 막히지 않도록, 알림음을 낼 오디오 컨텍스트를 클릭 시점에 미리 깨운다
    if (!timer.running) ensureAudio();
    toggleTimer();
  };

  const canStart = timer.finished ? timer.durationMs > 0 : timer.restMs > 0;
  const mainLabel = timer.running ? '일시정지' : timer.finished ? '다시 시작' : '시작';
  const caption = timer.finished
    ? '시간이 다 됐어요'
    : timer.running
      ? '남은 시간'
      : remaining < timer.durationMs
        ? '일시정지됨'
        : '시간을 정하고 시작하세요';

  return (
    <ToolScreen title="타이머" icon={<AlarmClock size={22} aria-hidden />}>
      <div className={styles.panel}>
        <div className={`${styles.ringWrap} ${timer.finished ? styles.ringFinished : ''}`}>
          <svg viewBox="0 0 44 44" className={styles.ring} aria-hidden>
            <circle
              cx="22"
              cy="22"
              r={RADIUS}
              fill="none"
              stroke="var(--color-border)"
              strokeWidth={STROKE}
            />
            <circle
              cx="22"
              cy="22"
              r={RADIUS}
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth={STROKE}
              strokeLinecap={dash > 1 ? 'round' : 'butt'}
              strokeDasharray={`${dash} ${100 - dash}`}
              strokeDashoffset={25}
            />
          </svg>

          <div className={styles.ringCenter}>
            {/* 시(hour) 자리가 붙으면 8글자까지 늘어나므로 링 안쪽을 넘지 않게 글자를 줄인다 */}
            <p
              className={`${styles.display} ${countdown.length > 5 ? styles.displayLong : ''}`}
              role="timer"
              aria-live="off"
            >
              {countdown}
            </p>
            <p className={styles.caption}>{caption}</p>
          </div>
        </div>

        {timer.finished && (
          <div className={styles.banner} role="status">
            <BellRing size={17} aria-hidden />
            <span className={styles.bannerText}>타이머가 끝났어요</span>
            <button type="button" className={styles.bannerButton} onClick={dismissTimerAlert}>
              확인
            </button>
          </div>
        )}

        <div className={styles.controls}>
          <button
            type="button"
            className={styles.subButton}
            onClick={resetTimer}
            disabled={timer.running ? false : remaining === timer.durationMs && !timer.finished}
          >
            <RotateCcw size={16} aria-hidden /> 리셋
          </button>

          <button
            type="button"
            className={`${styles.mainButton} ${timer.running ? styles.mainButtonPause : ''}`}
            onClick={handleToggle}
            disabled={!timer.running && !canStart}
          >
            {timer.running ? <Pause size={18} aria-hidden /> : <Play size={18} aria-hidden />}
            {mainLabel}
          </button>
        </div>

        <div className={styles.setup} aria-label="시간 설정">
          <div className={styles.inputRow}>
            {FIELD_DEFS.map((field, i) => (
              <Fragment key={field.key}>
                {i > 0 && <span className={styles.colon}>:</span>}
                <label className={styles.inputLabel}>
                  <input
                    type="text"
                    inputMode="numeric"
                    className={styles.numberInput}
                    value={fields[field.key]}
                    onChange={(e) => handleField(field.key, e.target.value)}
                    disabled={timer.running}
                    aria-label={field.label}
                  />
                  {field.label}
                </label>
              </Fragment>
            ))}
          </div>

          <div className={styles.presets}>
            {PRESETS.map((preset) => (
              <button
                type="button"
                key={preset.ms}
                className={`${styles.preset} ${
                  timer.durationMs === preset.ms ? styles.presetActive : ''
                }`}
                onClick={() => setTimerDuration(preset.ms)}
                disabled={timer.running}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </ToolScreen>
  );
}
