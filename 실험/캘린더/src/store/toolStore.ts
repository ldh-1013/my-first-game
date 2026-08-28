import { create } from 'zustand';
import { playChime } from '../utils/sound';

/**
 * 스톱워치·타이머 스토어.
 *
 * 왜 calendarStore와 분리했나:
 * calendarStore의 viewMode(월간/주간/성좌/감정)는 "캘린더를 어떤 방식으로 볼까"이고,
 * 여기의 screen은 "캘린더를 볼까, 아예 다른 도구를 볼까"라 층위가 다르다.
 * 섞으면 goPrev/goNext 같은 캘린더 전용 액션이 스톱워치 화면에서도 의미를 갖는 척하게 된다.
 *
 * 왜 시간 값을 스토어에 두나:
 * 화면을 나갔다 와도 흐르던 시간이 유지되어야 하므로, 컴포넌트 수명과 무관한 곳에 있어야 한다.
 * 저장하는 건 '경과 시간'이 아니라 '시작한 타임스탬프'다. 화면이 얼마나 자주 갱신되든,
 * 창이 가려져 있었든 상관없이 Date.now()와의 차이로 언제나 정확한 값이 나온다.
 */

export type ToolScreenName = 'calendar' | 'stopwatch' | 'timer' | 'rain';

export interface StopwatchState {
  running: boolean;
  /** 마지막으로 시작/재개한 시각(Date.now 기준). 멈춰 있으면 null */
  startedAt: number | null;
  /** 일시정지로 끊긴 이전 구간들의 누적 경과(ms) */
  base: number;
  /** 랩 기록 — 각 항목은 그 랩을 찍은 순간의 '총' 경과 시간(ms) */
  laps: number[];
}

export interface TimerState {
  running: boolean;
  /** 사용자가 설정한 총 시간(ms) */
  durationMs: number;
  /** 실행 중일 때 끝나는 시각(Date.now 기준). 멈춰 있으면 null */
  endsAt: number | null;
  /** 멈춰 있을 때 남은 시간(ms) */
  restMs: number;
  /** 완료 배너를 띄워야 하는지 */
  finished: boolean;
}

interface ToolStore {
  screen: ToolScreenName;
  stopwatch: StopwatchState;
  timer: TimerState;

  openTool: (name: Exclude<ToolScreenName, 'calendar'>) => void;
  closeTool: () => void;

  toggleStopwatch: () => void;
  resetStopwatch: () => void;
  addLap: () => void;

  setTimerDuration: (ms: number) => void;
  toggleTimer: () => void;
  resetTimer: () => void;
  dismissTimerAlert: () => void;
}

const DEFAULT_TIMER_MS = 5 * 60_000;
// 시/분/초 입력이 각각 두 자리이므로 99:59:59가 상한
const MAX_TIMER_MS = 99 * 3_600_000 + 59 * 60_000 + 59_000;

/** 지금 이 순간의 스톱워치 경과 시간(ms). 실행 중이면 시작 시각과의 차이를 더한다. */
export function stopwatchElapsed(sw: StopwatchState, now: number = Date.now()): number {
  return sw.running && sw.startedAt !== null ? sw.base + (now - sw.startedAt) : sw.base;
}

/** 지금 이 순간 타이머에 남은 시간(ms). */
export function timerRemaining(timer: TimerState, now: number = Date.now()): number {
  return timer.running && timer.endsAt !== null
    ? Math.max(timer.endsAt - now, 0)
    : timer.restMs;
}

/* ---------------------------------------------------------------------------
 * 타이머 알람
 *
 * 화면 갱신용 rAF와 별개로, '끝나는 순간'은 화면을 보고 있지 않아도 알아채야 한다.
 * 그래서 남은 시간만큼의 setTimeout 하나를 따로 예약한다. 창이 가려지면 브라우저가
 * 타이머를 늦추므로, 다시 보이거나 포커스를 얻을 때 endsAt을 기준으로 재확인한다.
 * ------------------------------------------------------------------------- */

let alarm: number | undefined;
let guardsAttached = false;

function clearAlarm(): void {
  if (alarm !== undefined) {
    window.clearTimeout(alarm);
    alarm = undefined;
  }
}

function scheduleAlarm(endsAt: number): void {
  clearAlarm();
  alarm = window.setTimeout(checkAlarm, Math.max(endsAt - Date.now(), 0));
}

/** 끝났으면 완료 처리, 아직이면 남은 만큼 다시 예약한다(늦게 깨어난 경우 대비). */
function checkAlarm(): void {
  clearAlarm();
  const { timer } = useToolStore.getState();
  if (!timer.running || timer.endsAt === null) return;

  if (timer.endsAt > Date.now()) {
    scheduleAlarm(timer.endsAt);
    return;
  }

  useToolStore.setState({
    timer: { ...timer, running: false, endsAt: null, restMs: 0, finished: true },
  });
  playChime();
}

function attachGuards(): void {
  if (guardsAttached) return;
  guardsAttached = true;
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) checkAlarm();
  });
  window.addEventListener('focus', checkAlarm);
}

export const useToolStore = create<ToolStore>((set) => ({
  screen: 'calendar',
  stopwatch: { running: false, startedAt: null, base: 0, laps: [] },
  timer: {
    running: false,
    durationMs: DEFAULT_TIMER_MS,
    endsAt: null,
    restMs: DEFAULT_TIMER_MS,
    finished: false,
  },

  openTool: (name) => set({ screen: name }),
  closeTool: () => set({ screen: 'calendar' }),

  toggleStopwatch: () =>
    set((state) => {
      const sw = state.stopwatch;
      if (sw.running) {
        // 일시정지: 지금까지 흐른 구간을 누적에 넣고 시작점을 비운다
        return { stopwatch: { ...sw, running: false, startedAt: null, base: stopwatchElapsed(sw) } };
      }
      return { stopwatch: { ...sw, running: true, startedAt: Date.now() } };
    }),

  resetStopwatch: () => set({ stopwatch: { running: false, startedAt: null, base: 0, laps: [] } }),

  addLap: () =>
    set((state) => {
      const total = stopwatchElapsed(state.stopwatch);
      if (total <= 0) return {};
      return { stopwatch: { ...state.stopwatch, laps: [...state.stopwatch.laps, total] } };
    }),

  setTimerDuration: (ms) =>
    set((state) => {
      // 돌아가는 중에 설정을 바꾸면 남은 시간의 의미가 흐려지므로 무시한다
      if (state.timer.running) return {};
      const durationMs = Math.min(Math.max(Math.round(ms), 0), MAX_TIMER_MS);
      return { timer: { ...state.timer, durationMs, restMs: durationMs, finished: false } };
    }),

  toggleTimer: () =>
    set((state) => {
      const timer = state.timer;

      if (timer.running) {
        clearAlarm();
        return { timer: { ...timer, running: false, endsAt: null, restMs: timerRemaining(timer) } };
      }

      // 이미 끝난 뒤 다시 누르면 설정값으로 새로 시작
      const rest = timer.finished ? timer.durationMs : timer.restMs;
      if (rest <= 0) return {};

      const endsAt = Date.now() + rest;
      attachGuards();
      scheduleAlarm(endsAt);
      return { timer: { ...timer, running: true, endsAt, restMs: rest, finished: false } };
    }),

  resetTimer: () =>
    set((state) => {
      clearAlarm();
      return {
        timer: {
          ...state.timer,
          running: false,
          endsAt: null,
          restMs: state.timer.durationMs,
          finished: false,
        },
      };
    }),

  dismissTimerAlert: () =>
    set((state) => ({
      timer: { ...state.timer, finished: false, restMs: state.timer.durationMs },
    })),
}));
