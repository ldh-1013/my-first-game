import { addDays } from 'date-fns';
import { CalendarClock } from 'lucide-react';
import { useMemo } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import type { CalendarEvent } from '../types/event';
import {
  eventsOnDate,
  formatUpcomingLabel,
  fromDateKey,
  groupEventsByDate,
  toDateKey,
} from '../utils/dateUtils';
import { EventRow } from './EventRow';
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
    // 하루씩 전체 목록을 훑으면 7번 순회하게 된다. 한 번 묶어 두고 7번 꺼내 쓴다.
    const eventsByDate = groupEventsByDate(events);
    const start = fromDateKey(todayKey);
    return Array.from({ length: 7 }, (_, i) => toDateKey(addDays(start, i)))
      .map((key) => ({ key, events: eventsOnDate(eventsByDate, key) }))
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
              <EventRow key={event.id} event={event} onOpen={openDate} />
            ))}
          </div>
        ))
      )}
    </section>
  );
}
