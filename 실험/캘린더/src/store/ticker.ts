import { useCallback, useSyncExternalStore } from 'react';

/**
 * 스톱워치/타이머 화면 갱신용 프레임 티커.
 *
 * store/clock.ts와 역할이 다르다. clock은 '지금 몇 시인가'를 초 경계에 맞춰 알려주지만,
 * 여기서는 1/100초까지 흐르는 숫자와 진행 링을 다시 그리기만 하면 된다.
 * 그래서 시간 값 자체는 저장하지 않고(경과·잔여는 언제나 타임스탬프 차이로 계산한다)
 * "다시 그려라"라는 신호만 requestAnimationFrame으로 내보낸다.
 *
 * setInterval로 값을 누적하지 않으므로 오차가 쌓이지 않고,
 * 창이 가려져 rAF가 멈춰도 다시 보이는 순간 실제 시각으로 계산되어 곧바로 맞춰진다.
 */

type Listener = () => void;

const listeners = new Set<Listener>();
let frameStamp = Date.now();
let raf: number | undefined;

function frame(): void {
  frameStamp = Date.now();
  // 스냅샷을 먼저 갱신한 뒤 알려야 useSyncExternalStore가 새 값을 읽는다
  listeners.forEach((listener) => listener());
  raf = requestAnimationFrame(frame);
}

function start(): void {
  if (raf === undefined && listeners.size > 0) raf = requestAnimationFrame(frame);
}

function stop(): void {
  if (raf !== undefined) {
    cancelAnimationFrame(raf);
    raf = undefined;
  }
}

function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  start();
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) stop();
  };
}

const IDLE_STAMP = 0;

/**
 * active일 때만 매 프레임 리렌더를 유발한다.
 * 흐르지 않는 상태(정지/일시정지)나 화면 밖에서는 구독조차 하지 않아 rAF가 돌지 않는다.
 */
export function useAnimationTick(active: boolean): number {
  const subscribeIfActive = useCallback(
    (listener: Listener) => (active ? subscribe(listener) : () => {}),
    [active],
  );
  return useSyncExternalStore(subscribeIfActive, () => (active ? frameStamp : IDLE_STAMP));
}
