import { describeError, reportRenderError } from './diagnostics';

/**
 * 리액트가 뜨기도 전에 죽는 경우를 받아 내는 그물.
 *
 * ErrorBoundary는 리액트 트리 안에서 난 에러만 잡는다. 그런데 "창은 뜨는데 안이 텅 빔"의
 * 흔한 범인은 그보다 앞 단계다 — 모듈 평가 중 예외(예: 어떤 환경에서 localStorage나
 * matchMedia 접근이 막힘), 스크립트 자체 로드 실패. 그때는 #root가 영영 비어 있고
 * 리액트는 시작조차 못 한다.
 *
 * 그래서 main.tsx 맨 위에서 이 모듈을 가장 먼저 import한다. window의 error 이벤트는
 * 모듈 평가 실패도 잡아 주므로, 여기서 로그로 남기고 최소한의 안내 화면을 직접 그린다
 * (리액트 없이 DOM으로만 — 리액트가 못 뜬 상황이라는 게 전제다).
 */

const FALLBACK_ID = 'boot-failure';

function paintFallback(summary: { message: string; stack: string | null }): void {
  const root = document.getElementById('root');
  // 리액트가 이미 뭔가 그렸다면 건드리지 않는다. 그 화면이 이 안내보다 낫다.
  if (!root || root.childElementCount > 0 || document.getElementById(FALLBACK_ID)) return;

  const box = document.createElement('div');
  box.id = FALLBACK_ID;
  box.setAttribute('role', 'alert');
  box.style.cssText =
    'max-width:560px;margin:60px auto;padding:28px;border-radius:20px;' +
    'background:var(--color-surface,#fff);color:var(--color-text-primary,#2e2a4a);' +
    'box-shadow:0 4px 20px rgba(0,0,0,0.12);font-family:inherit;line-height:1.7';

  const title = document.createElement('h1');
  title.textContent = '앱을 시작하지 못했어요';
  title.style.cssText = 'font-size:18px;font-weight:700;margin-bottom:10px';

  const lead = document.createElement('p');
  lead.textContent =
    '저장된 일정은 그대로 있어요. 아래 내용을 그대로 전해 주시면 원인을 찾는 데 큰 도움이 됩니다.';
  lead.style.cssText = 'font-size:13px;color:var(--color-text-secondary,#8a87a6);margin-bottom:16px';

  const message = document.createElement('p');
  message.textContent = summary.message;
  message.style.cssText =
    'font-size:13px;font-weight:600;padding:12px 14px;border-radius:10px;' +
    'background:var(--color-cell,#fbfbff);border:1px solid var(--color-border,#e4e1f7);word-break:break-word';

  box.append(title, lead, message);

  if (summary.stack) {
    const stack = document.createElement('pre');
    stack.textContent = summary.stack;
    stack.style.cssText =
      'margin-top:10px;max-height:220px;overflow:auto;font-size:11px;white-space:pre-wrap;' +
      'color:var(--color-text-secondary,#8a87a6);padding:12px 14px;border-radius:10px;' +
      'background:var(--color-cell,#fbfbff);border:1px solid var(--color-border,#e4e1f7)';
    box.append(stack);
  }

  const reload = document.createElement('button');
  reload.type = 'button';
  reload.textContent = '새로고침';
  reload.style.cssText =
    'margin-top:18px;padding:9px 18px;border:none;border-radius:999px;cursor:pointer;' +
    'font-size:13px;font-weight:600;background:var(--color-primary,#7c9eff);color:#fff';
  reload.addEventListener('click', () => location.reload());
  box.append(reload);

  root.append(box);
}

function handle(context: string, error: unknown): void {
  reportRenderError(context, error);
  try {
    paintFallback(describeError(error));
  } catch {
    /* 안내 화면조차 못 그리면 더는 할 수 있는 게 없다 */
  }
}

window.addEventListener('error', (event) => {
  handle('window-error', event.error ?? event.message);
});

window.addEventListener('unhandledrejection', (event) => {
  // 처리되지 않은 Promise 거부는 화면을 지우지는 않지만, 원인 추적에는 남겨 둘 값어치가 있다
  reportRenderError('unhandled-rejection', event.reason);
});
