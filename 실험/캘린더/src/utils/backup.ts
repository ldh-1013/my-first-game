import type { CalendarEvent } from '../types/event';

/**
 * 자동 백업 — 렌더러 쪽 창구.
 *
 * 실제 파일 쓰기는 electron/main.cjs가 하고, 여기서는 preload가 붙여 준
 * window.calendarBackup을 감싸기만 한다.
 *
 * 중요한 전제: 브라우저(npm run dev)에는 preload가 없어 이 API가 아예 없다.
 * 그때는 에러를 던지지 않고 조용히 아무것도 하지 않는다 — 백업은 Electron 앱에서만
 * 의미가 있는 기능이고, 개발 중에 콘솔이 시뻘개질 이유가 없다.
 */

export interface BackupStatus {
  dir: string;
  count: number;
  /** 마지막 백업 파일의 수정 시각(ms). 백업이 하나도 없으면 null */
  lastBackupAt: number | null;
  /** 오늘 날짜 백업이 이미 있는지 */
  todayDone: boolean;
}

interface BackupResult {
  ok: boolean;
  file?: string;
  dir?: string;
  reason?: string;
}

interface BackupApi {
  run: (json: string) => Promise<BackupResult>;
  cache: (json: string) => void;
  status: () => Promise<BackupStatus>;
  openFolder: () => Promise<string>;
}

declare global {
  interface Window {
    calendarBackup?: BackupApi;
  }
}

/** Electron에서 실행 중이고 백업 다리가 놓여 있는지 */
export function isBackupAvailable(): boolean {
  return typeof window !== 'undefined' && window.calendarBackup !== undefined;
}

/** 백업 파일에 담기는 형태. 수동 내보내기(이벤트 배열)와 달리 기분 기록까지 함께 담는다. */
export interface BackupPayload {
  version: 1;
  exportedAt: string;
  events: CalendarEvent[];
  moods: Record<string, number>;
}

function serialize(events: CalendarEvent[], moods: Record<string, number>): string {
  const payload: BackupPayload = {
    version: 1,
    exportedAt: new Date().toISOString(),
    events,
    moods,
  };
  return JSON.stringify(payload, null, 2);
}

/** 지금 즉시 백업 파일을 쓴다. Electron이 아니면 아무 일도 일어나지 않는다. */
export async function runBackup(
  events: CalendarEvent[],
  moods: Record<string, number>,
): Promise<void> {
  const api = window.calendarBackup;
  if (!api) return;
  try {
    await api.run(serialize(events, moods));
  } catch {
    /* 백업 실패로 앱이 멈추면 안 된다 */
  }
}

/**
 * 최신 데이터를 메인 프로세스에 맡겨 둔다. 이 호출만으로는 디스크에 쓰지 않는다.
 * 앱을 종료할 때 메인이 이 값으로 그날 백업을 덮어쓴다.
 */
export function cacheBackup(events: CalendarEvent[], moods: Record<string, number>): void {
  const api = window.calendarBackup;
  if (!api) return;
  try {
    api.cache(serialize(events, moods));
  } catch {
    /* 무시 */
  }
}

export async function getBackupStatus(): Promise<BackupStatus | null> {
  const api = window.calendarBackup;
  if (!api) return null;
  try {
    return await api.status();
  } catch {
    return null;
  }
}

export async function openBackupFolder(): Promise<void> {
  const api = window.calendarBackup;
  if (!api) return;
  try {
    await api.openFolder();
  } catch {
    /* 무시 */
  }
}
