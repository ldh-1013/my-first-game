/**
 * '컴퓨터 켤 때 할 일 확인' — 렌더러 쪽 창구.
 *
 * 켜면 앱이 Windows 로그인 항목에 등록돼, 로그인할 때 창 없이 떠서 할 일을 확인하고
 * 트레이에 머무른다. 등록 여부는 OS가 들고 있으므로 여기서는 저장하지 않고 매번 묻는다.
 *
 * backup.ts와 같은 전제: 브라우저(npm run dev)에는 이 창구가 없다.
 */

export interface StartupStatus {
  /** 설치본에서만 true. 개발 실행에서 등록하면 깨진 시작프로그램 항목이 남는다 */
  available: boolean;
  enabled: boolean;
}

interface StartupApi {
  status: () => Promise<StartupStatus>;
  set: (enabled: boolean) => Promise<StartupStatus>;
}

declare global {
  interface Window {
    calendarStartup?: StartupApi;
  }
}

export function isStartupAvailable(): boolean {
  return typeof window !== 'undefined' && window.calendarStartup !== undefined;
}

export async function getStartupStatus(): Promise<StartupStatus | null> {
  try {
    return (await window.calendarStartup?.status()) ?? null;
  } catch {
    return null;
  }
}

export async function setStartupEnabled(enabled: boolean): Promise<StartupStatus | null> {
  try {
    return (await window.calendarStartup?.set(enabled)) ?? null;
  } catch {
    return null;
  }
}
