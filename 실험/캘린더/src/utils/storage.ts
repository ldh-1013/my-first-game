import type { CalendarEvent, EventCategory } from '../types/event';
import type { TodoItem } from '../types/todo';
import { isThemePreference, type ThemePreference } from '../types/theme';
import type { WeatherLocation, WeatherSnapshot } from './weather';

const EVENTS_KEY = 'my-calendar-events';
const MOODS_KEY = 'my-calendar-moods';
const SETTINGS_KEY = 'my-calendar-settings';
const CELEBRATED_KEY = 'my-calendar-revealed';
const WEATHER_KEY = 'my-calendar-weather';
const TODOS_KEY = 'my-calendar-todos';

const VALID_CATEGORIES: EventCategory[] = ['work', 'personal', 'important', 'idea', 'custom'];

export interface AppSettings {
  bgEffect: boolean;
  /** 라이트/다크/시스템. 없으면 시스템 설정을 따른다 */
  theme?: ThemePreference;
  /** 사용자가 직접 고른 날씨 지역. 없으면 IP 기반으로 자동 감지한다 */
  weatherLocation?: WeatherLocation;
}

export const DEFAULT_SETTINGS: AppSettings = { bgEffect: true, theme: 'system' };

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
    (e.completed === undefined || typeof e.completed === 'boolean') &&
    typeof e.createdAt === 'string' &&
    typeof e.updatedAt === 'string'
  );
}

export function isValidTodo(value: unknown): value is TodoItem {
  if (typeof value !== 'object' || value === null) return false;
  const t = value as Record<string, unknown>;
  return (
    typeof t.id === 'string' &&
    typeof t.title === 'string' &&
    typeof t.dueDate === 'string' &&
    /^\d{4}-\d{2}-\d{2}$/.test(t.dueDate) &&
    typeof t.done === 'boolean' &&
    typeof t.createdAt === 'string' &&
    typeof t.updatedAt === 'string'
  );
}

/**
 * 백업/저장 문자열에서 할 일만 뽑아낸다. 이벤트와 같은 두 형태를 받는다:
 * 배열 그대로, 또는 { todos: [...] }를 담은 자동 백업 파일.
 * 할 일이 없던 시절의 백업에는 todos가 없으므로 그때는 null이다.
 */
export function parseTodos(raw: string): TodoItem[] | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed.filter(isValidTodo);
    if (typeof parsed === 'object' && parsed !== null) {
      const todos = (parsed as { todos?: unknown }).todos;
      if (Array.isArray(todos)) return todos.filter(isValidTodo);
    }
    return null;
  } catch {
    return null;
  }
}

export function loadTodos(): TodoItem[] {
  try {
    const raw = localStorage.getItem(TODOS_KEY);
    if (!raw) return [];
    return parseTodos(raw) ?? [];
  } catch {
    return [];
  }
}

/**
 * JSON 문자열을 파싱해 유효한 이벤트만 반환. JSON 자체가 잘못됐으면 null.
 *
 * 두 가지 형태를 받는다:
 *  - 이벤트 배열        → 수동 '내보내기'가 만드는 형태
 *  - { events: [...] }  → 자동 백업이 만드는 형태(기분 기록도 함께 담겨 있다)
 * 자동 백업 파일도 그대로 '불러오기'로 되살릴 수 있어야 해서 둘 다 받아들인다.
 */
export function parseEvents(raw: string): CalendarEvent[] | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed.filter(isValidEvent);
    if (typeof parsed === 'object' && parsed !== null) {
      const events = (parsed as { events?: unknown }).events;
      if (Array.isArray(events)) return events.filter(isValidEvent);
    }
    return null;
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

/** 외부에서 온 값이 아니어도 저장된 JSON은 손상될 수 있으므로 형태를 확인한다 */
function isValidLocation(value: unknown): value is WeatherLocation {
  if (typeof value !== 'object' || value === null) return false;
  const loc = value as Record<string, unknown>;
  return (
    typeof loc.name === 'string' &&
    loc.name.length > 0 &&
    typeof loc.lat === 'number' &&
    Number.isFinite(loc.lat) &&
    Math.abs(loc.lat) <= 90 &&
    typeof loc.lon === 'number' &&
    Number.isFinite(loc.lon) &&
    Math.abs(loc.lon) <= 180
  );
}

export function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    const settings: AppSettings = {
      bgEffect: typeof parsed.bgEffect === 'boolean' ? parsed.bgEffect : true,
    };
    if (isThemePreference(parsed.theme)) settings.theme = parsed.theme;
    if (isValidLocation(parsed.weatherLocation)) settings.weatherLocation = parsed.weatherLocation;
    return settings;
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
export const saveTodosDebounced = makeDebouncedSaver(TODOS_KEY);

/**
 * 설정은 즉시 저장 (토글은 드물게 발생).
 * 넘긴 항목만 덮어쓰고 나머지는 그대로 둔다 — 배경 효과를 끄는 것만으로
 * 저장해 둔 날씨 지역이 함께 날아가면 안 되기 때문이다.
 */
export function saveSettings(patch: Partial<AppSettings>): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify({ ...loadSettings(), ...patch }));
  } catch {
    /* 무시 */
  }
}

/**
 * 마지막으로 성공한 날씨 응답을 캐시한다.
 * 앱을 다시 켰을 때 네트워크를 기다리지 않고 직전 값을 먼저 보여주기 위한 것으로,
 * 최신값은 그 뒤 백그라운드 갱신으로 채워진다.
 */
export function loadWeatherCache(): WeatherSnapshot | null {
  try {
    const raw = localStorage.getItem(WEATHER_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) return null;
    const snap = parsed as Record<string, unknown>;
    const nullableNumber = (value: unknown) =>
      value === null || (typeof value === 'number' && Number.isFinite(value));
    // 확률이므로 0~100을 벗어난 값은 캐시가 망가진 것으로 본다
    const nullablePercent = (value: unknown) =>
      value === null || (typeof value === 'number' && value >= 0 && value <= 100);
    // 풍속·강수확률은 나중에 추가된 필드다. 값이 있는데 형태가 틀리면 버리되,
    // 아예 없는 옛 캐시는 아래에서 null로 채워 살린다 (업데이트 직후 캐시가 통째로 날아가지 않게).
    const addedLater = (value: unknown, check: (v: unknown) => boolean) =>
      value === undefined || check(value);
    // 시간대별 비 예보 — null이거나, hour/probability/amount 모양을 갖춘 배열이어야 한다
    const nullableHourly = (value: unknown) =>
      value === null ||
      (Array.isArray(value) &&
        value.every((row) => {
          if (typeof row !== 'object' || row === null) return false;
          const r = row as Record<string, unknown>;
          return (
            typeof r.hour === 'number' &&
            r.hour >= 0 &&
            r.hour <= 23 &&
            nullableNumber(r.probability) &&
            nullableNumber(r.amount)
          );
        }));
    if (
      typeof snap.fetchedAt !== 'number' ||
      !isValidLocation(snap.location) ||
      typeof snap.temperature !== 'number' ||
      typeof snap.apparentTemperature !== 'number' ||
      typeof snap.weatherCode !== 'number' ||
      typeof snap.isDay !== 'boolean' ||
      !addedLater(snap.windSpeed, nullableNumber) ||
      !addedLater(snap.rainChancePercent, nullablePercent) ||
      !addedLater(snap.hourlyRain, nullableHourly) ||
      !nullableNumber(snap.pm10) ||
      !nullableNumber(snap.pm25)
    ) {
      return null;
    }
    return {
      ...snap,
      windSpeed: (snap.windSpeed as number | null | undefined) ?? null,
      rainChancePercent: (snap.rainChancePercent as number | null | undefined) ?? null,
      hourlyRain: (snap.hourlyRain as WeatherSnapshot['hourlyRain'] | undefined) ?? null,
    } as WeatherSnapshot;
  } catch {
    return null;
  }
}

export function saveWeatherCache(snapshot: WeatherSnapshot): void {
  try {
    localStorage.setItem(WEATHER_KEY, JSON.stringify(snapshot));
  } catch {
    /* 무시 */
  }
}
