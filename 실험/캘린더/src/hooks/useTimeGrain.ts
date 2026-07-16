import { useEffect } from 'react';
import { DEFAULT_GRADIENT, getTimeBand, TIME_GRADIENTS } from '../utils/timeGrain';

/**
 * 켜져 있으면 시간대에 따라 --bg-gradient CSS 변수를 매분 갱신한다.
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
      const band = getTimeBand(new Date().getHours());
      root.style.setProperty('--bg-gradient', TIME_GRADIENTS[band]);
    };

    apply();
    const id = window.setInterval(apply, 60_000);
    return () => window.clearInterval(id);
  }, [enabled]);
}
