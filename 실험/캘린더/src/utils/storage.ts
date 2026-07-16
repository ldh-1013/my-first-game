import type { CalendarEvent, EventCategory } from '../types/event';

const EVENTS_KEY = 'my-calendar-events';
const MOODS_KEY = 'my-calendar-moods';
const SETTINGS_KEY = 'my-calendar-settings';
const CELEBRATED_KEY = 'my-calendar-revealed';

const VALID_CATEGORIES: EventCategory[] = ['work', 'personal', 'important', 'idea', 'custom'];

export interface AppSettings {
  bgEffect: boolean;
}

export const DEFAULT_SETTINGS: AppSettings = { bgEffect: true };

export function isValidEvent(value: unknown): value is CalendarEvent {
  if (typeof value !== 'object' || value === null) return false;
  const e = value as Record<string, unknown>;
  return (
    typeof e.id === 'string' &&
    typeof e.date === 'string' &&
    /^\d{4}-\d{2}-\d{2}$/.test(e.date) &&
    (e.time === undefined || (typeof e.time === 'string' && /^\d{2}:\d{2}$/.test(e.time))) &&
    typeof e.title === 'string' &&
    (e.memo === undefined || typeof e.memo === 'string') &&
    VALID_CATEGORIES.includes(e.category as EventCategory) &&
    (e.color === undefined || typeof e.color === 'string') &&
    (e.projectTag === undefined || typeof e.projectTag === 'string') &&
    (e.isSealed === undefined || typeof e.isSealed === 'boolean') &&
    (e.sealedUntil === undefined ||
      (typeof e.sealedUntil === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(e.sealedUntil))) &&
    typeof e.createdAt === 'string' &&
    typeof e.updatedAt === 'string'
  );
}

/** JSON 문자열을 파싱해 유효한 이벤트만 반환. JSON 자체가 잘못됐거나 배열이 아니면 null */
export function parseEvents(raw: string): CalendarEvent[] | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    return parsed.filter(isValidEvent);
  } catch {
    return null;
  }
}

export function loadEvents(): CalendarEvent[] {
  try {
    const raw = localStorage.getItem(EVENTS_KEY);
    if (!raw) return [];
    return parseEvents(raw) ?? [];
  } catch {
    return [];
  }
}

/** 기분 기록: { 'YYYY-MM-DD': 1..5 } */
export function loadMoods(): Record<string, number> {
  try {
    const raw = localStorage.getItem(MOODS_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) return {};
    const result: Record<string, number> = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (/^\d{4}-\d{2}-\d{2}$/.test(key) && typeof value === 'number' && value >= 1 && value <= 5) {
        result[key] = value;
      }
    }
    return result;
  } catch {
    return {};
  }
}

export function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return { bgEffect: typeof parsed.bgEffect === 'boolean' ? parsed.bgEffect : true };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function loadCelebratedIds(): string[] {
  try {
    const raw = localStorage.getItem(CELEBRATED_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

export function saveCelebratedIds(ids: string[]): void {
  try {
    localStorage.setItem(CELEBRATED_KEY, JSON.stringify(ids));
  } catch {
    /* 무시 */
  }
}

function makeDebouncedSaver(key: string): (value: unknown) => void {
  let timer: number | undefined;
  return (value: unknown) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch {
        /* 저장 공간 부족 등 — 개인용 앱이므로 조용히 무시 */
      }
    }, 300);
  };
}

export const saveEventsDebounced = makeDebouncedSaver(EVENTS_KEY);
export const saveMoodsDebounced = makeDebouncedSaver(MOODS_KEY);

/** 설정은 즉시 저장 (토글은 드물게 발생) */
export function saveSettings(settings: AppSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    /* 무시 */
  }
}
