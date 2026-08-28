import { CATEGORIES, type CalendarEvent, type EventCategory } from '../types/event';
import { MOOD_LEVELS, type MoodLevel } from './mood';

/**
 * 리캡 화면이 쓰는 집계 — 순수 함수만 둔다.
 *
 * 화면에서 분리해 둔 이유는 두 가지다. 계산을 눈이 아니라 값으로 검증할 수 있고,
 * 월간과 연간이 같은 세는 방식을 공유하게 된다(월간은 'yyyy-MM', 연간은 'yyyy'로
 * 접두어만 달라진다).
 *
 * 톤에 대한 전제: 여기서는 세기만 하고 평가하지 않는다. "많다/적다"의 판단은
 * 문구로도, 임계값으로도 만들지 않는다.
 */

export interface CategoryCount {
  category: EventCategory;
  count: number;
  /** 0~1. 전체가 0이면 0 */
  fraction: number;
}

export interface MoodCount {
  level: MoodLevel;
  count: number;
  fraction: number;
}

export interface BusiestDay {
  dateKey: string;
  count: number;
}

export interface PeriodRecap {
  /** 'yyyy-MM'(월간) 또는 'yyyy'(연간) */
  prefix: string;
  total: number;
  completed: number;
  /** 완료 비율 0~1. 일정이 없으면 0 */
  completedRatio: number;
  categories: CategoryCount[];
  busiestDay: BusiestDay | null;
  moods: MoodCount[];
  /** 기분을 남긴 날 수 */
  moodDays: number;
  /** 그 기간에 새로 봉인한 캡슐 수 (일정 날짜 기준) */
  sealedCount: number;
  /** 그 기간에 개봉일이 도래한 캡슐 수 */
  unsealedCount: number;
}

function countCategories(events: CalendarEvent[]): CategoryCount[] {
  const counts = new Map<EventCategory, number>();
  for (const event of events) counts.set(event.category, (counts.get(event.category) ?? 0) + 1);
  return CATEGORIES.filter((category) => (counts.get(category) ?? 0) > 0).map((category) => {
    const count = counts.get(category) ?? 0;
    return { category, count, fraction: events.length > 0 ? count / events.length : 0 };
  });
}

function findBusiestDay(events: CalendarEvent[]): BusiestDay | null {
  const perDay = new Map<string, number>();
  for (const event of events) perDay.set(event.date, (perDay.get(event.date) ?? 0) + 1);
  let best: BusiestDay | null = null;
  // 같은 개수면 앞선 날짜를 남긴다 — 순서가 흔들리지 않아야 다시 열어도 같은 날이 나온다
  for (const [dateKey, count] of [...perDay].sort((a, b) => a[0].localeCompare(b[0]))) {
    if (!best || count > best.count) best = { dateKey, count };
  }
  return best;
}

function countMoods(moods: Record<string, number>, prefix: string): { list: MoodCount[]; days: number } {
  const counts = new Map<MoodLevel, number>();
  let days = 0;
  for (const [dateKey, level] of Object.entries(moods)) {
    if (!dateKey.startsWith(prefix)) continue;
    if (!MOOD_LEVELS.includes(level as MoodLevel)) continue;
    counts.set(level as MoodLevel, (counts.get(level as MoodLevel) ?? 0) + 1);
    days += 1;
  }
  const list = MOOD_LEVELS.filter((level) => (counts.get(level) ?? 0) > 0).map((level) => {
    const count = counts.get(level) ?? 0;
    return { level, count, fraction: days > 0 ? count / days : 0 };
  });
  return { list, days };
}

/**
 * 한 기간(prefix로 자른다)의 집계.
 * prefix가 '2026-08'이면 그달, '2026'이면 그해다.
 */
export function periodRecap(
  events: CalendarEvent[],
  moods: Record<string, number>,
  prefix: string,
): PeriodRecap {
  const inPeriod = events.filter((event) => event.date.startsWith(prefix));
  const completed = inPeriod.filter((event) => event.completed).length;
  const { list: moodList, days: moodDays } = countMoods(moods, prefix);

  return {
    prefix,
    total: inPeriod.length,
    completed,
    completedRatio: inPeriod.length > 0 ? completed / inPeriod.length : 0,
    categories: countCategories(inPeriod),
    busiestDay: findBusiestDay(inPeriod),
    moods: moodList,
    moodDays,
    sealedCount: inPeriod.filter((event) => event.isSealed).length,
    // 개봉일이 이 기간 안에 있는 캡슐 — 일정 자체는 다른 달에 있어도 이 기간에 '열린' 것이다
    unsealedCount: events.filter(
      (event) => event.isSealed && event.sealedUntil?.startsWith(prefix),
    ).length,
  };
}

/** 연간 화면의 12개월 막대. 일정이 없는 달도 0으로 자리를 지킨다 */
export function monthlyCounts(events: CalendarEvent[], year: number): number[] {
  const counts = new Array<number>(12).fill(0);
  const prefix = `${year}-`;
  for (const event of events) {
    if (!event.date.startsWith(prefix)) continue;
    const month = Number(event.date.slice(5, 7));
    if (month >= 1 && month <= 12) counts[month - 1] += 1;
  }
  return counts;
}

/** 가장 일정이 많았던 달(0-based). 전부 0이면 null */
export function busiestMonth(counts: number[]): number | null {
  let best: number | null = null;
  counts.forEach((count, index) => {
    if (count > 0 && (best === null || count > counts[best])) best = index;
  });
  return best;
}
