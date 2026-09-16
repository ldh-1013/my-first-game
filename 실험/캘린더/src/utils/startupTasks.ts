/**
 * 앱을 켤 때 한 번 도는 일들이 끝났는지 모아 보는 곳.
 *
 * 로그인 항목으로 조용히 뜬 실행은 할 일을 확인하고 나면 숨은 창을 내려 메모리를
 * 돌려준다. 그런데 켤 때 도는 일이 알림 판정만은 아니다 — 자동 백업도 "오늘 백업이
 * 없으면 만든다"를 비동기로 돈다(IPC 왕복 2번). 알림만 보고 창을 내리면 그날의
 * 자동 백업이 잘린다. 그래서 둘 다 끝났을 때만 메인에 "확인 끝"을 알린다.
 *
 * 각 작업은 성공·실패·건너뜀과 무관하게 반드시 한 번 끝났다고 알린다.
 * 하나라도 안 알리면 메인은 안전 타임아웃까지 창을 붙잡고 있게 된다.
 */

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

const todoNotice = deferred();
const startupBackup = deferred();

export function markTodoNoticeSettled(): void {
  todoNotice.resolve();
}

export function markStartupBackupSettled(): void {
  startupBackup.resolve();
}

/** 켤 때 도는 일이 모두 끝나면 풀린다 */
export function startupTasksSettled(): Promise<void> {
  return Promise.all([todoNotice.promise, startupBackup.promise]).then(() => undefined);
}
