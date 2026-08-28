import { useEffect, useMemo, useRef } from 'react';
import { useNow, useTodayKey } from '../store/clock';
import { useCalendarStore } from '../store/calendarStore';
import { getEventColor, type CalendarEvent } from '../types/event';
import { eventsOnDate, getWeekDays, groupEventsByDate, toDateKey } from '../utils/dateUtils';
import { getHoliday } from '../utils/holidays';
import styles from './WeekView.module.css';

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
const START_HOUR = 6;
const END_HOUR = 24;
const HOUR_HEIGHT = 52;
const HOURS = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);

interface PositionedEvent {
  event: CalendarEvent;
  column: number;
  columns: number;
}

function toMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
}

/** 시작 시각이 1시간 이내로 겹치는 일정끼리 묶어 가로로 나눠 배치 */
function layoutDayEvents(events: CalendarEvent[]): PositionedEvent[] {
  const sorted = [...events].sort((a, b) => a.time!.localeCompare(b.time!));
  const result: PositionedEvent[] = [];
  let cluster: CalendarEvent[] = [];
  let clusterEnd = -1;

  const flush = () => {
    cluster.forEach((event, index) =>
      result.push({ event, column: index, columns: cluster.length }),
    );
    cluster = [];
  };

  for (const event of sorted) {
    const start = toMinutes(event.time!);
    if (cluster.length > 0 && start >= clusterEnd) flush();
    cluster.push(event);
    clusterEnd = Math.max(clusterEnd, start + 60);
  }
  flush();
  return result;
}

export function WeekView() {
  const viewDate = useCalendarStore((s) => s.viewDate);
  const events = useCalendarStore((s) => s.events);
  const selectDate = useCalendarStore((s) => s.selectDate);
  const todayKey = useTodayKey();

  const days = useMemo(() => getWeekDays(viewDate), [viewDate]);
  const eventsByDate = useMemo(() => groupEventsByDate(events), [events]);

  // 현재 시각선은 분 단위로만 움직이면 충분하다(중앙 시계 공유).
  const now = useNow('minute');

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // 처음 열 때 현재 시각 근처(없으면 오전 8시)로 스크롤
    const hour = Math.max(now.getHours() - 1, START_HOUR + 1);
    scrollRef.current?.scrollTo({ top: (Math.min(hour, 20) - START_HOUR) * HOUR_HEIGHT });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const nowTop = (now.getHours() + now.getMinutes() / 60 - START_HOUR) * HOUR_HEIGHT;

  return (
    <div className={styles.weekView}>
      <div className={styles.headerRow}>
        <div className={styles.gutterSpacer} />
        {days.map((day) => {
          const key = toDateKey(day);
          const isToday = key === todayKey;
          const holiday = getHoliday(key);
          return (
            <button
              type="button"
              key={key}
              className={`${styles.dayHeader} ${isToday ? styles.dayHeaderToday : ''} ${
                holiday ? styles.dayHeaderHoliday : ''
              }`}
              onClick={() => selectDate(key)}
            >
              {/* 요일 이름은 배열 순서가 아니라 날짜 자체에서 뽑는다 —
                  배열이 어떤 이유로든 일요일에서 시작하지 않더라도 라벨은 항상 진짜 요일을 가리킨다 */}
              <span
                className={`${styles.dayName} ${
                  day.getDay() === 0 ? styles.sunday : day.getDay() === 6 ? styles.saturday : ''
                }`}
              >
                {WEEKDAYS[day.getDay()]}
              </span>
              <span
                className={`${styles.dayDate} ${isToday ? styles.dayDateToday : ''} ${
                  holiday && !isToday ? styles.dayDateHoliday : ''
                }`}
              >
                {day.getDate()}
              </span>
              {holiday && (
                <span className={styles.dayHoliday} title={holiday.name}>
                  {holiday.name}
                  {holiday.isProjected ? ' (예상)' : ''}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className={styles.allDayRow}>
        <div className={styles.gutterLabel}>종일</div>
        {days.map((day) => {
          const key = toDateKey(day);
          const allDay = eventsOnDate(eventsByDate, key).filter((event) => !event.time);
          return (
            <div key={key} className={styles.allDayCell}>
              {allDay.map((event) => (
                <button
                  type="button"
                  key={event.id}
                  className={`${styles.allDayChip} ${event.completed ? styles.chipDone : ''}`}
                  style={{
                    background: `color-mix(in srgb, ${getEventColor(event)} 24%, var(--color-chip-base))`,
                  }}
                  onClick={() => selectDate(key)}
                  title={event.title}
                >
                  {event.title}
                </button>
              ))}
            </div>
          );
        })}
      </div>

      <div className={styles.scrollArea} ref={scrollRef}>
        <div className={styles.gutter}>
          {HOURS.map((hour) => (
            <div key={hour} className={styles.hourLabel}>
              {String(hour).padStart(2, '0')}:00
            </div>
          ))}
        </div>
        <div className={styles.dayColumns}>
          {days.map((day) => {
            const key = toDateKey(day);
            const isToday = key === todayKey;
            const timed = eventsOnDate(eventsByDate, key).filter((event) => event.time);
            const positioned = layoutDayEvents(timed);

            return (
              <div
                key={key}
                className={`${styles.dayColumn} ${isToday ? styles.dayColumnToday : ''}`}
                onClick={() => selectDate(key)}
              >
                {positioned.map(({ event, column, columns }) => {
                  const startMinutes = Math.max(toMinutes(event.time!), START_HOUR * 60);
                  const top = ((startMinutes - START_HOUR * 60) / 60) * HOUR_HEIGHT;
                  const width = 100 / columns;
                  return (
                    <button
                      type="button"
                      key={event.id}
                      className={`${styles.eventChip} ${event.completed ? styles.chipDone : ''}`}
                      style={{
                        top: Math.min(top, (END_HOUR - START_HOUR - 1) * HOUR_HEIGHT) + 2,
                        height: HOUR_HEIGHT - 5,
                        left: `calc(${column * width}% + 2px)`,
                        width: `calc(${width}% - 5px)`,
                        background: `color-mix(in srgb, ${getEventColor(event)} 26%, var(--color-chip-base))`,
                        borderLeftColor: getEventColor(event),
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        selectDate(key);
                      }}
                      title={`${event.time} ${event.title}`}
                    >
                      <span className={styles.eventTime}>{event.time}</span>
                      <span className={styles.eventTitle}>{event.title}</span>
                    </button>
                  );
                })}
                {isToday && nowTop >= 0 && nowTop <= (END_HOUR - START_HOUR) * HOUR_HEIGHT && (
                  <div className={styles.nowLine} style={{ top: nowTop }} aria-hidden />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
