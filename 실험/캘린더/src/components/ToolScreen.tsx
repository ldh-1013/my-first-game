import { ArrowLeft } from 'lucide-react';
import type { ReactNode } from 'react';
import { useToolStore } from '../store/toolStore';
import styles from './ToolScreen.module.css';

interface ToolScreenProps {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}

/**
 * 스톱워치·타이머가 공유하는 전체 화면 껍데기.
 * 좌측 상단 뒤로가기 버튼과 제목만 담당하고, 안쪽은 각 도구가 채운다.
 * (Esc 단축키는 화면이 하나만 활성인 App에서 한 번만 등록한다 — 여기 두면
 *  숨어 있는 다른 도구 화면까지 리스너를 걸어 중복된다.)
 */
export function ToolScreen({ title, icon, children }: ToolScreenProps) {
  const closeTool = useToolStore((s) => s.closeTool);

  return (
    <section className={styles.screen} aria-label={title}>
      <header className={styles.topBar}>
        <button
          type="button"
          className={styles.backButton}
          aria-label="캘린더로 돌아가기"
          onClick={closeTool}
        >
          <ArrowLeft size={18} />
        </button>
        <h2 className={styles.title}>
          {icon}
          {title}
        </h2>
        <p className={styles.hint}>
          <kbd>Esc</kbd> 로 캘린더 돌아가기
        </p>
      </header>

      <div className={styles.stage}>{children}</div>
    </section>
  );
}
