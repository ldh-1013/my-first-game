import { isSameMonth } from 'date-fns';
import { Lock } from 'lucide-react';
import { useMemo } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { getEventColor, isLocked } from '../types/event';
import {
  WEEKDAY_LABELS,
  eventsOnDate,
  getMonthGridDays,
  groupEventsByDate,
  toDateKey,
} from '../utils/dateUtils';
import { getHoliday } from '../utils/holidays';
import { MoonPhase } from './MoonPhase';
import styles from './CalendarGrid.module.css';

const MAX_DOTS = 4;

/** '설날 대체' -> '설날'. 연휴가 이어지는지 판단할 때 대체공휴일도 같은 묶음으로 본다 */
function holidayGroup(name: string): string {
  return name.replace(' 대체', '');
}

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
        {WEEKDAY_LABELS.map((label, index) => (
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
        {days.map((day, index) => {
          const key = toDateKey(day);
          const holiday = getHoliday(key);
          // 설날·추석처럼 사흘이 이어지는 연휴는 안쪽 모서리를 각지게 깎아 한 덩어리로 읽히게 한다.
          // 줄이 바뀌는 곳(일요일 칸의 왼쪽, 토요일 칸의 오른쪽)에서는 이어붙이지 않는다.
          const sameRun = (offset: number) => {
            if (!holiday) return false;
            const neighbor = days[index + offset];
            if (!neighbor) return false;
            const other = getHoliday(toDateKey(neighbor));
            return other !== null && holidayGroup(other.name) === holidayGroup(holiday.name);
          };
          const joinPrev = index % 7 !== 0 && sameRun(-1);
          const joinNext = index % 7 !== 6 && sameRun(1);
          const dayEvents = eventsOnDate(eventsByDate, key);
          const preview = dayEvents[0];
          const previewLocked = preview ? isLocked(preview, todayKey) : false;
          const weekday = day.getDay();
          const classNames = [styles.cell];
          if (!isSameMonth(day, viewDate)) classNames.push(styles.outside);
          if (holiday) classNames.push(styles.holiday);
          if (holiday?.isSubstitute) classNames.push(styles.holidaySubstitute);
          if (holiday?.isProjected) classNames.push(styles.holidayProjected);
          if (joinPrev) classNames.push(styles.joinPrev);
          if (joinNext) classNames.push(styles.joinNext);
          if (key === todayKey) classNames.push(styles.today);
          if (key === selectedDate) classNames.push(styles.selected);

          return (
            <button
              type="button"
              key={key}
              className={classNames.join(' ')}
              onClick={() => selectDate(key)}
              aria-label={`${day.getMonth() + 1}월 ${day.getDate()}일${
                holiday ? `, 공휴일 ${holiday.name}${holiday.isProjected ? ' (예상)' : ''}` : ''
              }, 일정 ${dayEvents.length}개`}
            >
              <span className={styles.cellHead}>
                <span
                  className={`${styles.dayNumber} ${
                    holiday
                      ? styles.holidayNumber
                      : weekday === 0
                        ? styles.sundayNumber
                        : weekday === 6
                          ? styles.saturdayNumber
                          : ''
                  }`}
                >
                  {day.getDate()}
                </span>
                {bgEffect && <MoonPhase date={day} size={13} />}
              </span>
              {holiday && (
                <span
                  className={styles.holidayLabel}
                  title={
                    holiday.isSubstitute
                      ? `${holiday.name} (원래 공휴일 ${holiday.substituteFor})`
                      : holiday.name
                  }
                >
                  {holiday.name}
                  {holiday.isProjected && <em className={styles.holidayGuess}>예상</em>}
                </span>
              )}
              {preview && (
                <span
                  className={`${styles.preview} ${previewLocked ? styles.previewLocked : ''} ${
                    preview.completed ? styles.previewDone : ''
                  }`}
                  style={{
                    background: `color-mix(in srgb, ${getEventColor(preview)} 22%, var(--color-chip-base))`,
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
