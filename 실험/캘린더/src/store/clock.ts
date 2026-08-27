import { useSyncExternalStore } from 'react';
import { toDateKey } from '../utils/dateUtils';

/**
 * 앱 전체가 공유하는 단일 시계.
 *
 * - Electron 렌더러의 `new Date()`는 OS(Windows) 시스템 시계를 그대로 읽으므로
 *   이 모듈이 곧 "실시간 윈도우 시계"다. 흩어져 있던 setInterval을 하나로 모아
 *   모든 화면이 동일한 순간을 근거로 렌더링하도록 한다.
 * - 틱은 매 초 경계(다음 정각 초)에 맞춰 setTimeout으로 스스로 다시 예약한다.
 *   setInterval처럼 오차가 누적되지 않고, 표시되는 초가 벽시계와 어긋나지 않는다.
 * - 창이 포커스를 얻거나 다시 보이게 되면(절전/대기에서 복귀 포함) 즉시 재동기화한다.
 * - 구독은 grain(초/분/일) 단위로 나뉘어, 각 화면은 필요한 만큼만 다시 그린다.
 *   초 단위 시계는 매초, "오늘"은 자정에만 갱신되지만 근거가 되는 시각은 하나다.
 */

type Grain = 'second' | 'minute' | 'day';
type Listener = () => void;

const listeners: Record<Grain, Set<Listener>> = {
  second: new Set(),
  minute: new Set(),
  day: new Set(),
};

function minuteStamp(d: Date): number {
  return Math.floor(d.getTime() / 60_000);
}

let lastSecond = Math.floor(Date.now() / 1000);
let lastMinute = minuteStamp(new Date());

// grain별 스냅샷: 해당 grain이 실제로 바뀔 때만 참조가 갱신되어야
// useSyncExternalStore가 불필요하게 다시 그리지 않는다.
let secondSnapshot = new Date();
let minuteSnapshot = secondSnapshot;
let daySnapshot = toDateKey(secondSnapshot);

let timer: number | undefined;
let globalsAttached = false;

function totalListeners(): number {
  return listeners.second.size + listeners.minute.size + listeners.day.size;
}

/** 시스템 시계를 다시 읽어 바뀐 grain의 구독자에게만 알린다. */
function tick(): void {
  const now = new Date();

  const sec = Math.floor(now.getTime() / 1000);
  if (sec !== lastSecond) {
    lastSecond = sec;
    secondSnapshot = now;
    listeners.second.forEach((l) => l());
  }

  const min = minuteStamp(now);
  if (min !== lastMinute) {
    lastMinute = min;
    minuteSnapshot = now;
    listeners.minute.forEach((l) => l());
  }

  const day = toDateKey(now);
  if (day !== daySnapshot) {
    daySnapshot = day;
    listeners.day.forEach((l) => l());
  }
}

function scheduleNext(): void {
  // 다음 정각 초까지 남은 시간만큼만 기다린다 → 드리프트가 쌓이지 않는다.
  const delay = 1000 - (Date.now() % 1000);
  timer = window.setTimeout(() => {
    timer = undefined;
    tick();
    if (totalListeners() > 0 && !document.hidden) scheduleNext();
  }, delay);
}

function start(): void {
  if (timer !== undefined || document.hidden || totalListeners() === 0) return;
  tick(); // 시작하자마자 즉시 동기화
  scheduleNext();
}

function stop(): void {
  if (timer !== undefined) {
    window.clearTimeout(timer);
    timer = undefined;
  }
}

function onVisibilityChange(): void {
  if (document.hidden) stop();
  else start(); // 다시 보이면 start()가 즉시 tick()으로 재동기화
}

function onFocusOrResume(): void {
  // 절전/대기 복귀처럼 visibilitychange가 안 오는 경우까지 커버
  tick();
  start();
}

function attachGlobals(): void {
  if (globalsAttached) return;
  globalsAttached = true;
  document.addEventListener('visibilitychange', onVisibilityChange);
  window.addEventListener('focus', onFocusOrResume);
  window.addEventListener('online', onFocusOrResume);
}

function subscribe(grain: Grain, listener: Listener): () => void {
  attachGlobals();
  listeners[grain].add(listener);
  start();
  return () => {
    listeners[grain].delete(listener);
    if (totalListeners() === 0) stop();
  };
}

/** 지금 이 순간의 시각을 한 번 읽는다(클릭 핸들러 등 일회성 용도). */
export function getNow(): Date {
  return new Date();
}

/** 오늘 날짜 키('YYYY-MM-DD')를 한 번 읽는다. */
export function getTodayKey(): string {
  return toDateKey(new Date());
}

/** 공유 시계를 grain 단위로 구독한다. 반환된 Date는 같은 틱 안에서 모든 구독자가 동일하다. */
export function useNow(grain: 'second' | 'minute' = 'second'): Date {
  return useSyncExternalStore(
    (cb) => subscribe(grain, cb),
    () => (grain === 'minute' ? minuteSnapshot : secondSnapshot),
  );
}

/** 자정을 넘어가면 1초 안에 갱신되는 오늘 날짜 키. 앱 전체가 같은 값을 공유한다. */
export function useTodayKey(): string {
  return useSyncExternalStore(
    (cb) => subscribe('day', cb),
    () => daySnapshot,
  );
}

/** 부수효과 훅 등에서 공유 시계의 분 단위 변화를 직접 구독할 때 사용. */
export function subscribeMinute(listener: Listener): () => void {
  return subscribe('minute', listener);
}
