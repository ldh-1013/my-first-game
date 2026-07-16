export type EventCategory = 'work' | 'personal' | 'important' | 'idea' | 'custom';

export interface CalendarEvent {
  id: string;
  date: string; // 'YYYY-MM-DD'
  time?: string; // 'HH:MM', 없으면 하루종일 일정
  title: string;
  memo?: string;
  category: EventCategory;
  color?: string; // category가 'custom'일 때 사용자 지정 hex
  projectTag?: string; // 성좌 뷰에서 묶이는 자유 프로젝트 태그
  isSealed?: boolean; // 타임캡슐 봉인 여부
  sealedUntil?: string; // 'YYYY-MM-DD' 이 날짜 전까지 잠김
  createdAt: string;
  updatedAt: string;
}

export type EventInput = Omit<CalendarEvent, 'id' | 'createdAt' | 'updatedAt'>;

export const CATEGORIES: EventCategory[] = ['work', 'personal', 'important', 'idea', 'custom'];

export const CATEGORY_LABELS: Record<EventCategory, string> = {
  work: '업무',
  personal: '개인',
  important: '중요',
  idea: '아이디어',
  custom: '직접 지정',
};

export const CATEGORY_COLORS: Record<EventCategory, string> = {
  work: 'var(--color-work)',
  personal: 'var(--color-personal)',
  important: 'var(--color-important)',
  idea: 'var(--color-idea)',
  custom: 'var(--color-secondary)',
};

export function getEventColor(event: Pick<CalendarEvent, 'category' | 'color'>): string {
  if (event.category === 'custom' && event.color) return event.color;
  return CATEGORY_COLORS[event.category];
}

/** 봉인된 타임캡슐이 아직 잠겨 있는지 (오늘 < 개봉일) */
export function isLocked(event: CalendarEvent, todayKey: string): boolean {
  return Boolean(event.isSealed && event.sealedUntil && todayKey < event.sealedUntil);
}

/** 성좌 뷰에서 사용할 태그: 프로젝트 태그 우선, 없으면 카테고리 라벨 */
export function tagOf(event: CalendarEvent): string {
  const tag = event.projectTag?.trim();
  return tag ? tag : CATEGORY_LABELS[event.category];
}
