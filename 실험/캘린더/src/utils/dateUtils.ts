import {
  differenceInCalendarDays,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  parse,
  startOfMonth,
  startOfWeek,
} from 'date-fns';
import { ko } from 'date-fns/locale';
import type { CalendarEvent } from '../types/event';

export const DATE_KEY_FORMAT = 'yyyy-MM-dd';

export function toDateKey(date: Date): string {
  return format(date, DATE_KEY_FORMAT);
}

export function fromDateKey(key: string): Date {
  return parse(key, DATE_KEY_FORMAT, new Date());
}

/** 월 그리드에 표시할 날짜들 (앞뒤 달 포함, 일요일 시작) */
export function getMonthGridDays(anchor: Date): Date[] {
  const start = startOfWeek(startOfMonth(anchor));
  const end = endOfWeek(endOfMonth(anchor));
  return eachDayOfInterval({ start, end });
}

export function getWeekDays(anchor: Date): Date[] {
  return eachDayOfInterval({ start: startOfWeek(anchor), end: endOfWeek(anchor) });
}

export function formatMonthTitle(date: Date): string {
  return format(date, 'yyyy년 M월');
}

export function formatWeekRange(anchor: Date): string {
  const days = getWeekDays(anchor);
  return `${format(days[0], 'M월 d일')} – ${format(days[6], 'M월 d일')}`;
}

export function formatDayTitle(key: string): string {
  return format(fromDateKey(key), 'M월 d일 EEEE', { locale: ko });
}

export function formatUpcomingLabel(key: string, todayKey: string): string {
  const diff = differenceInCalendarDays(fromDateKey(key), fromDateKey(todayKey));
  if (diff === 0) return '오늘';
  if (diff === 1) return '내일';
  return format(fromDateKey(key), 'M월 d일 (EEE)', { locale: ko });
}

/** 하루종일 일정이 먼저, 그 다음 시간순 */
export function compareEvents(a: CalendarEvent, b: CalendarEvent): number {
  if (!a.time && !b.time) return a.createdAt.localeCompare(b.createdAt);
  if (!a.time) return -1;
  if (!b.time) return 1;
  return a.time.localeCompare(b.time) || a.createdAt.localeCompare(b.createdAt);
}

export function groupEventsByDate(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
  const map = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const list = map.get(event.date);
    if (list) list.push(event);
    else map.set(event.date, [event]);
  }
  for (const list of map.values()) list.sort(compareEvents);
  return map;
}
