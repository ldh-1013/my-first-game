import { useEffect } from 'react';
import { getNow, subscribeMinute } from '../store/clock';
import { DEFAULT_GRADIENT, getTimeBand, TIME_GRADIENTS } from '../utils/timeGrain';

/**
 * 켜져 있으면 시간대에 따라 --bg-gradient CSS 변수를 갱신한다.
 * 중앙 시계의 분 단위 변화를 구독하므로, 화면의 시계·날짜와 완전히 같은 순간을 근거로 한다.
 * body의 background transition(3s)이 부드럽게 이어받아 스냅되지 않고 흘러간다.
 */
export function useTimeGrain(enabled: boolean): void {
  useEffect(() => {
    const root = document.documentElement;

    if (!enabled) {
      root.style.setProperty('--bg-gradient', DEFAULT_GRADIENT);
      return;
    }

    const apply = () => {
      const band = getTimeBand(getNow().getHours());
      root.style.setProperty('--bg-gradient', TIME_GRADIENTS[band]);
    };

    apply();
    return subscribeMinute(apply);
  }, [enabled]);
}
