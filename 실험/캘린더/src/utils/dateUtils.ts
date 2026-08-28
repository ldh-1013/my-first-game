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

/**
 * 요일 라벨. 인덱스가 Date.getDay()와 같아(0=일요일) 그대로 색인해 쓸 수 있고,
 * 아래 WEEK_OPTIONS(일요일 시작)와 짝을 이룬다 — 한쪽만 바꾸면 헤더와 날짜가 어긋난다.
 */
export const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'] as const;

export function toDateKey(date: Date): string {
  return format(date, DATE_KEY_FORMAT);
}

export function fromDateKey(key: string): Date {
  return parse(key, DATE_KEY_FORMAT, new Date());
}

/**
 * 주의 시작 요일을 일요일로 못박는다.
 *
 * CalendarGrid/WeekView는 ['일','월',...,'토'] 고정 헤더를 그려 놓고 날짜를 배열 순서대로
 * 흘려보내므로, 그리드가 일요일에서 시작한다는 전제가 깨지면 달 전체가 한 칸씩 밀린다.
 * date-fns의 기본값도 0이라 지금 동작은 그대로지만, 어딘가에서 setDefaultOptions로
 * 월요일 시작 로케일(예: de, enGB)을 지정하는 순간 헤더와 어긋나 버린다.
 * 암묵적 기본값에 기대지 않고 명시해서 그 사고를 원천 차단한다.
 */
const WEEK_OPTIONS = { weekStartsOn: 0 } as const;

/** 월 그리드에 표시할 날짜들 (앞뒤 달 포함, 일요일 시작) */
export function getMonthGridDays(anchor: Date): Date[] {
  const start = startOfWeek(startOfMonth(anchor), WEEK_OPTIONS);
  const end = endOfWeek(endOfMonth(anchor), WEEK_OPTIONS);
  return eachDayOfInterval({ start, end });
}

export function getWeekDays(anchor: Date): Date[] {
  return eachDayOfInterval({
    start: startOfWeek(anchor, WEEK_OPTIONS),
    end: endOfWeek(anchor, WEEK_OPTIONS),
  });
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

/** 날짜 키('YYYY-MM-DD') → 그날의 일정들. 각 배열은 compareEvents 순으로 정렬돼 있다. */
export type EventsByDate = Map<string, CalendarEvent[]>;

export function groupEventsByDate(events: CalendarEvent[]): EventsByDate {
  const map = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const list = map.get(event.date);
    if (list) list.push(event);
    else map.set(event.date, [event]);
  }
  for (const list of map.values()) list.sort(compareEvents);
  return map;
}

/**
 * 그룹에서 하루치를 꺼낸다. 일정이 없는 날이 대부분이라 호출부마다 `?? []`를 달게 되는데,
 * 그 기본값을 여기 한 곳에 둔다. 반환 배열은 groupEventsByDate가 이미 정렬해 둔 것이라
 * 호출부에서 다시 sort할 필요가 없다.
 */
export function eventsOnDate(map: EventsByDate, key: string): CalendarEvent[] {
  return map.get(key) ?? [];
}
