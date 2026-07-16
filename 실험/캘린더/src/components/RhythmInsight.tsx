import { Sparkles } from 'lucide-react';
import { useMemo } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { computeInsight } from '../utils/insight';
import styles from './RhythmInsight.module.css';

export function RhythmInsight() {
  const events = useCalendarStore((s) => s.events);
  const todayKey = useTodayKey();

  // events/todayKey가 바뀔 때만 재계산 (내부 랜덤도 이때만 다시 뽑힘)
  const message = useMemo(() => computeInsight(events, todayKey), [events, todayKey]);

  return (
    <div className={styles.banner} role="status">
      <span className={styles.iconWrap}>
        <Sparkles size={15} aria-hidden />
      </span>
      <p className={styles.text}>
        <span className={styles.label}>오늘의 리듬</span>
        {message}
      </p>
    </div>
  );
}
