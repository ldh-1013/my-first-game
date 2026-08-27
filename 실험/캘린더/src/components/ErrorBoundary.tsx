import { Component, type ErrorInfo, type ReactNode } from 'react';
import {
  describeError,
  isDiagnosticsAvailable,
  openLogFolder,
  reportRenderError,
} from '../utils/diagnostics';
import styles from './ErrorBoundary.module.css';

/**
 * 최상위 에러 바운더리.
 *
 * 리액트는 렌더링 도중 예외가 하나라도 새어 나오면 트리를 통째로 언마운트한다.
 * 그러면 창은 떠 있는데 안은 텅 빈 화면이 남는다 — 프로덕션에서는 그 이유를
 * 알려 줄 콘솔도, 로그도 없다. 그래서 여기서 잡아 (1) 화면에 무슨 일이 있었는지
 * 보여 주고 (2) 같은 내용을 로그 파일로도 남긴다.
 *
 * 이 바운더리가 못 잡는 것: 모듈 평가 단계(첫 import)에서 터지는 에러.
 * 그건 리액트가 뜨기도 전이라 bootGuard.ts가 window 에러 이벤트로 받아 낸다.
 */

interface Props {
  children: ReactNode;
}

interface State {
  message: string | null;
  stack: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { message: null, stack: null };

  static getDerivedStateFromError(error: unknown): State {
    return describeError(error);
  }

  componentDidCatch(error: unknown, info: ErrorInfo): void {
    // 컴포넌트 스택은 "어느 화면에서" 났는지 알려 주므로 로그에 같이 남긴다
    reportRenderError(`error-boundary${info.componentStack ?? ''}`, error);
  }

  render(): ReactNode {
    const { message, stack } = this.state;
    if (message === null) return this.props.children;

    return (
      <div className={styles.screen} role="alert">
        <div className={styles.card}>
          <h1 className={styles.title}>화면을 그리는 중 문제가 생겼어요</h1>
          <p className={styles.lead}>
            저장된 일정은 그대로 있어요. 아래 내용을 그대로 전해 주시면 원인을 찾는 데 큰 도움이
            됩니다.
          </p>

          <p className={styles.message}>{message}</p>
          {stack && <pre className={styles.stack}>{stack}</pre>}

          <div className={styles.actions}>
            <button type="button" className={styles.primary} onClick={() => location.reload()}>
              새로고침
            </button>
            {isDiagnosticsAvailable() && (
              <button type="button" className={styles.secondary} onClick={() => void openLogFolder()}>
                오류 로그 폴더 열기
              </button>
            )}
          </div>

          {isDiagnosticsAvailable() && (
            <p className={styles.note}>
              같은 내용이 render-errors.log 파일에도 기록됐어요.
            </p>
          )}
        </div>
      </div>
    );
  }
}
