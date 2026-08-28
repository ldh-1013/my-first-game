import { isSameMonth } from 'date-fns';
import { Lock } from 'lucide-react';
import { memo, useMemo } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { getEventColor, isLocked, type CalendarEvent } from '../types/event';
import {
  WEEKDAY_LABELS,
  eventsOnDate,
  getMonthGridDays,
  groupEventsByDate,
  toDateKey,
} from '../utils/dateUtils';
import { getHoliday, type Holiday } from '../utils/holidays';
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
          return (
            <CalendarCell
              key={key}
              day={day}
              dateKey={key}
              events={eventsOnDate(eventsByDate, key)}
              holiday={holiday}
              joinPrev={index % 7 !== 0 && sameRun(-1)}
              joinNext={index % 7 !== 6 && sameRun(1)}
              outside={!isSameMonth(day, viewDate)}
              isToday={key === todayKey}
              isSelected={key === selectedDate}
              todayKey={todayKey}
              showMoon={bgEffect}
              onSelect={selectDate}
            />
          );
        })}
      </div>
    </div>
  );
}

interface CalendarCellProps {
  day: Date;
  dateKey: string;
  /** 그날의 일정 (정렬된 상태). 일정 없는 날은 항상 같은 빈 배열을 받는다 */
  events: CalendarEvent[];
  holiday: Holiday | null;
  joinPrev: boolean;
  joinNext: boolean;
  outside: boolean;
  isToday: boolean;
  isSelected: boolean;
  todayKey: string;
  showMoon: boolean;
  /** 스토어 액션을 그대로 받는다 — 참조가 고정이라 memo가 유지된다 */
  onSelect: (key: string) => void;
}

/**
 * 날짜 한 칸.
 *
 * 한 달이면 42칸이라, 날짜를 하나 고르거나 오늘이 바뀌는 것만으로 42칸이 전부
 * 다시 계산되면 아깝다. memo로 감싸 자기 값이 바뀐 칸만 다시 그린다.
 * 그러려면 props가 렌더마다 새로 만들어지지 않아야 한다:
 *  - events: groupEventsByDate가 만든 배열(빈 날은 공용 빈 배열)
 *  - holiday: getHolidayMap이 연도별로 캐시한 객체
 *  - onSelect: zustand 액션 (참조 고정)
 */
const CalendarCell = memo(function CalendarCell({
  day,
  dateKey,
  events,
  holiday,
  joinPrev,
  joinNext,
  outside,
  isToday,
  isSelected,
  todayKey,
  showMoon,
  onSelect,
}: CalendarCellProps) {

  const preview = events[0];
  const previewLocked = preview ? isLocked(preview, todayKey) : false;
  const weekday = day.getDay();
  const classNames = [styles.cell];
  if (outside) classNames.push(styles.outside);
  if (holiday) classNames.push(styles.holiday);
  if (holiday?.isSubstitute) classNames.push(styles.holidaySubstitute);
  if (holiday?.isProjected) classNames.push(styles.holidayProjected);
  if (joinPrev) classNames.push(styles.joinPrev);
  if (joinNext) classNames.push(styles.joinNext);
  if (isToday) classNames.push(styles.today);
  if (isSelected) classNames.push(styles.selected);

  return (
    <button
      type="button"
      className={classNames.join(' ')}
      onClick={() => onSelect(dateKey)}
      aria-label={`${day.getMonth() + 1}월 ${day.getDate()}일${
        holiday ? `, 공휴일 ${holiday.name}${holiday.isProjected ? ' (예상)' : ''}` : ''
      }, 일정 ${events.length}개`}
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
        {showMoon && <MoonPhase date={day} size={13} />}
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
      {events.length > 1 && (
        <span className={styles.dots}>
          {events.slice(1, 1 + MAX_DOTS).map((event) => (
            <span
              key={event.id}
              className={styles.dot}
              style={{ background: getEventColor(event) }}
            />
          ))}
          {events.length > 1 + MAX_DOTS && (
            <span className={styles.more}>+{events.length - 1 - MAX_DOTS}</span>
          )}
        </span>
      )}
    </button>
  );
});
