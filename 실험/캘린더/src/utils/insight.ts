import { addDays, startOfWeek } from 'date-fns';
import type { CalendarEvent } from '../types/event';
import { WEEKDAY_LABELS, fromDateKey, toDateKey } from './dateUtils';

// 조건별 문구 후보 — 차분하고 관찰적인 톤, 재촉/평가하지 않음
const LIGHTER = ['이번 주는 평소보다 한결 여유로워요.', '이번 주는 조금 느긋한 흐름이에요.'];
const BUSIER = ['이번 주는 조금 바쁘게 흘러가고 있어요.', '이번 주는 평소보다 일정이 촘촘하네요.'];
const CALM = [
  '오늘도 차분히 하루를 기록해보세요.',
  '기록이 하나씩 쌓여가고 있어요.',
  '지금의 리듬을 편안히 이어가 보세요.',
];

function pick(list: string[]): string {
  return list[Math.floor(Math.random() * list.length)];
}

/**
 * 최근 4주 대비 이번 주 리듬을 규칙 기반으로 분석해 한 문장을 고른다.
 * AI/외부 호출 없이 로컬 계산만 사용.
 */
export function computeInsight(events: CalendarEvent[], todayKey: string): string {
  const today = fromDateKey(todayKey);
  const byDate = new Map<string, number>();
  for (const event of events) byDate.set(event.date, (byDate.get(event.date) ?? 0) + 1);

  const countRange = (start: Date, days: number): number => {
    let total = 0;
    for (let i = 0; i < days; i++) total += byDate.get(toDateKey(addDays(start, i))) ?? 0;
    return total;
  };

  const weekStart = startOfWeek(today);
  const baselineTotal = countRange(addDays(weekStart, -28), 28); // 지난 4주
  const baselineWeekAvg = baselineTotal / 4;
  const thisWeekCount = countRange(weekStart, 7);

  const matches: string[] = [];

  // 특정 요일에 일정이 몰린 경우
  let peakDay = -1;
  let peakCount = 0;
  for (let i = 0; i < 7; i++) {
    const count = byDate.get(toDateKey(addDays(weekStart, i))) ?? 0;
    if (count > peakCount) {
      peakCount = count;
      peakDay = i;
    }
  }
  if (thisWeekCount >= 3 && peakCount >= 2 && peakCount >= thisWeekCount * 0.5) {
    matches.push(`이번 주는 ${WEEKDAY_LABELS[peakDay]}요일에 일정이 몰려 있어요.`);
  }

  // 최근 7일 중 빈 날이 3일 이상
  let emptyDays = 0;
  for (let i = 0; i < 7; i++) {
    if ((byDate.get(toDateKey(addDays(today, -i))) ?? 0) === 0) emptyDays++;
  }
  if (emptyDays >= 3) {
    matches.push('최근 며칠 비어있는 시간이 많았어요.');
  }

  // 평소 대비 한산 / 분주 (기준 데이터가 있을 때만)
  if (baselineTotal >= 2) {
    if (thisWeekCount <= baselineWeekAvg * 0.6) matches.push(pick(LIGHTER));
    else if (thisWeekCount >= baselineWeekAvg * 1.4) matches.push(pick(BUSIER));
  }

  if (matches.length === 0) return pick(CALM);
  return matches[Math.floor(Math.random() * matches.length)];
}
