import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { ArrowRight, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import styles from './ClockWidget.module.css';

export function ClockWidget() {
  const [now, setNow] = useState(() => new Date());
  const todayKey = useTodayKey();
  const openDate = useCalendarStore((s) => s.openDate);
  const todayCount = useCalendarStore(
    (s) => s.events.filter((event) => event.date === todayKey).length,
  );

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <section className={styles.clock} aria-label="현재 시각">
      <div>
        <p className={styles.date}>{format(now, 'yyyy년 M월 d일 EEEE', { locale: ko })}</p>
        <p className={styles.time}>
          {format(now, 'HH:mm')}
          <span className={styles.seconds}>:{format(now, 'ss')}</span>
        </p>
      </div>
      <button type="button" className={styles.todayChip} onClick={() => openDate(todayKey)}>
        <Sparkles size={15} className={styles.chipIcon} aria-hidden />
        {todayCount > 0 ? `오늘 일정 ${todayCount}개` : '오늘은 일정이 없어요'}
        <ArrowRight size={14} aria-hidden />
      </button>
    </section>
  );
}
