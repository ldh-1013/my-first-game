import { isSameMonth } from 'date-fns';
import { Lock } from 'lucide-react';
import { useMemo } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { getEventColor, isLocked } from '../types/event';
import { getMonthGridDays, groupEventsByDate, toDateKey } from '../utils/dateUtils';
import { MoonPhase } from './MoonPhase';
import styles from './CalendarGrid.module.css';

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
const MAX_DOTS = 4;

export function CalendarGrid() {
  const viewDate = useCalendarStore((s) => s.viewDate);
  const events = useCalendarStore((s) => s.events);
  const selectedDate = useCalendarStore((s) => s.selectedDate);
  const selectDate = useCalendarStore((s) => s.selectDate);
  const bgEffect = useCalendarStore((s) => s.bgEffect);
  const todayKey = useTodayKey();

  const days = useMemo(() => getMonthGridDays(viewDate), [viewDate]);
  const eventsByDate = useMemo(() => groupEventsByDate(events), [events]);

  return (
    <div className={styles.grid}>
      <div className={styles.weekdayRow}>
        {WEEKDAYS.map((label, index) => (
          <span
            key={label}
            className={`${styles.weekday} ${
              index === 0 ? styles.sunday : index === 6 ? styles.saturday : ''
            }`}
          >
            {label}
          </span>
        ))}
      </div>
      <div className={styles.cells}>
        {days.map((day) => {
          const key = toDateKey(day);
          const dayEvents = eventsByDate.get(key) ?? [];
          const preview = dayEvents[0];
          const previewLocked = preview ? isLocked(preview, todayKey) : false;
          const weekday = day.getDay();
          const classNames = [styles.cell];
          if (!isSameMonth(day, viewDate)) classNames.push(styles.outside);
          if (key === todayKey) classNames.push(styles.today);
          if (key === selectedDate) classNames.push(styles.selected);

          return (
            <button
              type="button"
              key={key}
              className={classNames.join(' ')}
              onClick={() => selectDate(key)}
              aria-label={`${day.getMonth() + 1}월 ${day.getDate()}일, 일정 ${dayEvents.length}개`}
            >
              <span className={styles.cellHead}>
                <span
                  className={`${styles.dayNumber} ${
                    weekday === 0 ? styles.sundayNumber : weekday === 6 ? styles.saturdayNumber : ''
                  }`}
                >
                  {day.getDate()}
                </span>
                {bgEffect && <MoonPhase date={day} size={13} />}
              </span>
              {preview && (
                <span
                  className={`${styles.preview} ${previewLocked ? styles.previewLocked : ''}`}
                  style={{
                    background: `color-mix(in srgb, ${getEventColor(preview)} 22%, white)`,
                  }}
                >
                  {previewLocked ? (
                    <>
                      <Lock size={10} aria-hidden />
                      <span className={styles.previewBlur}>{preview.title}</span>
                    </>
                  ) : (
                    <>
                      {preview.time && <span className={styles.previewTime}>{preview.time}</span>}
                      {preview.title}
                    </>
                  )}
                </span>
              )}
              {dayEvents.length > 1 && (
                <span className={styles.dots}>
                  {dayEvents.slice(1, 1 + MAX_DOTS).map((event) => (
                    <span
                      key={event.id}
                      className={styles.dot}
                      style={{ background: getEventColor(event) }}
                    />
                  ))}
                  {dayEvents.length > 1 + MAX_DOTS && (
                    <span className={styles.more}>+{dayEvents.length - 1 - MAX_DOTS}</span>
                  )}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
