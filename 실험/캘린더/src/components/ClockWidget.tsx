import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { ArrowRight, Sparkles } from 'lucide-react';
import { useNow, useTodayKey } from '../store/clock';
import { useCalendarStore } from '../store/calendarStore';
import styles from './ClockWidget.module.css';

export function ClockWidget() {
  const now = useNow('second');
  const todayKey = useTodayKey();
  const openDate = useCalendarStore((s) => s.openDate);
  const todayCount = useCalendarStore(
    (s) => s.events.filter((event) => event.date === todayKey).length,
  );

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
