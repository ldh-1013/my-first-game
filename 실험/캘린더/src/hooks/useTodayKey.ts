import { useEffect, useState } from 'react';
import { toDateKey } from '../utils/dateUtils';

/** 자정이 넘어가면 자동으로 갱신되는 오늘 날짜 키 (매분 체크) */
export function useTodayKey(): string {
  const [todayKey, setTodayKey] = useState(() => toDateKey(new Date()));

  useEffect(() => {
    const id = window.setInterval(() => {
      const key = toDateKey(new Date());
      setTodayKey((prev) => (prev === key ? prev : key));
    }, 60_000);
    return () => window.clearInterval(id);
  }, []);

  return todayKey;
}
