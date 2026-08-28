import { memo } from 'react';
import { getEventColor, type CalendarEvent } from '../types/event';
import styles from './EventRow.module.css';

/**
 * 사이드바 위젯에서 일정 한 건을 보여주는 줄 (점 · 시간 · 제목).
 *
 * '다가오는 일정'과 '1년 전 오늘'이 같은 모양을 쓰므로 한 곳에 둔다.
 * 누르면 그 날짜를 여는 것까지 같은 동작이라, 어느 날짜를 열지는 호출부가 정한다
 * (다가오는 일정은 일정의 날짜, 회고는 1년 전 날짜).
 *
 * memo: 부모(위젯)는 events나 오늘 날짜가 바뀔 때마다 다시 그려지는데,
 * onOpen으로 zustand 액션을 그대로 받으면 참조가 고정이라 실제로 바뀐 줄만 다시 그린다.
 */
interface EventRowProps {
  event: CalendarEvent;
  /** 눌렀을 때 열 날짜 키. 없으면 일정 자신의 날짜 */
  openKey?: string;
  onOpen: (date: string) => void;
}

export const EventRow = memo(function EventRow({ event, openKey, onOpen }: EventRowProps) {
  return (
    <button
      type="button"
      className={`${styles.item} ${event.completed ? styles.itemDone : ''}`}
      onClick={() => onOpen(openKey ?? event.date)}
    >
      <span className={styles.dot} style={{ background: getEventColor(event) }} />
      <span className={styles.time}>{event.time ?? '종일'}</span>
      <span className={styles.title}>{event.title}</span>
    </button>
  );
});
