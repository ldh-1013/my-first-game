import { subYears } from 'date-fns';
import { History } from 'lucide-react';
import { useMemo } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { isLocked } from '../types/event';
import { eventsOnDate, formatDayTitle, fromDateKey, groupEventsByDate, toDateKey } from '../utils/dateUtils';
import { EventRow } from './EventRow';
import styles from './OnThisDay.module.css';

/**
 * 정확히 1년 전 오늘 무엇을 적어 두었는지 돌아보는 위젯.
 *
 * 보여줄 게 없으면 자리를 차지하지 않는다 — 사이드바는 매일 보는 곳이라
 * "지난해 오늘은 비어 있었어요" 같은 빈 카드가 늘 떠 있으면 소음이 된다.
 * (날씨 위젯이 비 소식 줄을 조건부로만 보여주는 것과 같은 결.)
 *
 * 잠긴 타임캡슐은 빼고 센다. 아직 개봉일이 오지 않은 캡슐을 회고랍시고
 * 미리 펼쳐 보여주면 봉인의 의미가 없다.
 */
export function OnThisDay() {
  const events = useCalendarStore((s) => s.events);
  const openDate = useCalendarStore((s) => s.openDate);
  const todayKey = useTodayKey();

  const { dateKey, items } = useMemo(() => {
    // 2월 29일은 date-fns가 2월 28일로 당겨 준다(3월 1일로 밀리지 않는다)
    const key = toDateKey(subYears(fromDateKey(todayKey), 1));
    const all = eventsOnDate(groupEventsByDate(events), key);
    return { dateKey: key, items: all.filter((event) => !isLocked(event, todayKey)) };
  }, [events, todayKey]);

  if (items.length === 0) return null;

  return (
    <section className={styles.widget} aria-label="1년 전 오늘">
      <h2 className={styles.widgetTitle}>
        <History size={16} aria-hidden /> 1년 전 오늘
        <span className={styles.widgetSub}>{formatDayTitle(dateKey)}</span>
      </h2>
      {items.map((event) => (
        <EventRow key={event.id} event={event} openKey={dateKey} onOpen={openDate} />
      ))}
    </section>
  );
}
