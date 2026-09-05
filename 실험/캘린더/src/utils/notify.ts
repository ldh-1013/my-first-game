/**
 * 할 일 알림 — 렌더러 쪽 창구.
 *
 * 렌더러는 샌드박스라 OS 알림을 직접 못 띄운다(파일 쓰기와 같은 사정). 남은 할 일
 * 개수만 메인에 넘기고, 문구를 만들고 '하루 한 번'을 판정하는 건 메인이 한다.
 *
 * backup.ts·diagnostics.ts와 같은 전제: 브라우저(npm run dev)에는 이 창구가 없다.
 * 그때는 조용히 아무것도 하지 않는다.
 */

export interface TodoNoticeCounts {
  /** 오늘 마감인 미완료 개수 */
  today: number;
  /** 기한이 지난 미완료 개수 */
  overdue: number;
}

export interface TodoNoticeResult {
  shown: boolean;
  reason?: string;
  body?: string;
}

interface NotifyApi {
  todos: (counts: TodoNoticeCounts) => Promise<TodoNoticeResult>;
}

declare global {
  interface Window {
    calendarNotify?: NotifyApi;
  }
}

/** Electron에서 실행 중이고 알림 다리가 놓여 있는지 */
export function isNotifyAvailable(): boolean {
  return typeof window !== 'undefined' && window.calendarNotify !== undefined;
}

/** 남은 할 일을 알린다. 실패해도 조용히 넘어간다 — 알림 때문에 앱이 흔들릴 이유가 없다. */
export async function notifyTodos(counts: TodoNoticeCounts): Promise<TodoNoticeResult> {
  if (counts.today + counts.overdue <= 0) return { shown: false, reason: 'empty' };
  try {
    return (await window.calendarNotify?.todos(counts)) ?? { shown: false, reason: 'no-bridge' };
  } catch {
    return { shown: false, reason: 'error' };
  }
}
