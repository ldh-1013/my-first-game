/**
 * 오류 진단 — 렌더러 쪽 창구.
 *
 * 화면이 하얗게 비어 버리면 사용자는 아무것도 볼 수 없고, 프로덕션 빌드에는
 * 콘솔을 열어 줄 사람도 없다. 그래서 렌더러에서 잡은 에러를 메인 프로세스로 넘겨
 * userData 폴더의 render-errors.log에 남긴다. 사용자는 그 파일만 보내 주면 된다.
 *
 * backup.ts와 같은 전제: 브라우저(npm run dev)에는 preload가 없어 이 API가 없다.
 * 그때는 조용히 아무것도 하지 않고, 에러는 어차피 개발자 콘솔에 그대로 보인다.
 */

interface DiagnosticsApi {
  report: (message: string) => void;
  openLogFolder: () => Promise<string>;
}

declare global {
  interface Window {
    calendarDiagnostics?: DiagnosticsApi;
  }
}

/** Electron에서 실행 중이고 진단 다리가 놓여 있는지 */
export function isDiagnosticsAvailable(): boolean {
  return typeof window !== 'undefined' && window.calendarDiagnostics !== undefined;
}

export interface ErrorSummary {
  message: string;
  stack: string | null;
}

/** 무엇이 던져졌는지 모르는 값(문자열·객체·Error)을 사람이 읽을 수 있는 형태로 */
export function describeError(error: unknown): ErrorSummary {
  if (error instanceof Error) {
    return { message: error.message || error.name, stack: error.stack ?? null };
  }
  if (typeof error === 'string') return { message: error, stack: null };
  try {
    return { message: JSON.stringify(error), stack: null };
  } catch {
    return { message: String(error), stack: null };
  }
}

/**
 * 에러 한 건을 로그 파일로 넘긴다. 실패해도 조용히 넘어간다 —
 * 오류를 기록하려다 또 오류를 내면 원래 화면까지 같이 잃는다.
 */
export function reportRenderError(context: string, error: unknown): void {
  const { message, stack } = describeError(error);
  try {
    window.calendarDiagnostics?.report(
      [
        `renderer/${context}`,
        `message=${message}`,
        `url=${window.location.href}`,
        `ua=${navigator.userAgent}`,
        stack ? `stack=\n${stack}` : 'stack=none',
      ].join(' | '),
    );
  } catch {
    /* 무시 */
  }
}

export async function openLogFolder(): Promise<void> {
  try {
    await window.calendarDiagnostics?.openLogFolder();
  } catch {
    /* 무시 */
  }
}
