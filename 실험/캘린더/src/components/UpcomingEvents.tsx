import { addDays } from 'date-fns';
import { CalendarClock } from 'lucide-react';
import { useMemo } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { getEventColor, type CalendarEvent } from '../types/event';
import { compareEvents, formatUpcomingLabel, fromDateKey, toDateKey } from '../utils/dateUtils';
import styles from './UpcomingEvents.module.css';

interface DayGroup {
  key: string;
  events: CalendarEvent[];
}

export function UpcomingEvents() {
  const events = useCalendarStore((s) => s.events);
  const openDate = useCalendarStore((s) => s.openDate);
  const todayKey = useTodayKey();

  const groups = useMemo<DayGroup[]>(() => {
    const start = fromDateKey(todayKey);
    return Array.from({ length: 7 }, (_, i) => toDateKey(addDays(start, i)))
      .map((key) => ({
        key,
        events: events.filter((event) => event.date === key).sort(compareEvents),
      }))
      .filter((group) => group.events.length > 0);
  }, [events, todayKey]);

  return (
    <section className={styles.widget} aria-label="다가오는 일정">
      <h2 className={styles.widgetTitle}>
        <CalendarClock size={16} aria-hidden /> 다가오는 일정
        <span className={styles.widgetSub}>7일</span>
      </h2>
      {groups.length === 0 ? (
        <p className={styles.empty}>
          앞으로 7일간 일정이 없어요.
          <br />
          여유로운 한 주가 될 것 같아요 🍃
        </p>
      ) : (
        groups.map((group) => (
          <div key={group.key} className={styles.group}>
            <h3
              className={`${styles.groupLabel} ${
                group.key === todayKey ? styles.groupLabelToday : ''
              }`}
            >
              {formatUpcomingLabel(group.key, todayKey)}
            </h3>
            {group.events.map((event) => (
              <button
                type="button"
                key={event.id}
                className={styles.item}
                onClick={() => openDate(event.date)}
              >
                <span className={styles.dot} style={{ background: getEventColor(event) }} />
                <span className={styles.time}>{event.time ?? '종일'}</span>
                <span className={styles.title}>{event.title}</span>
              </button>
            ))}
          </div>
        ))
      )}
    </section>
  );
}
