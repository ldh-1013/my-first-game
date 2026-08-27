import type { CSSProperties, ReactNode } from 'react';
import styles from './SegmentedControl.module.css';

/**
 * 강조 배경이 미끄러지는 세그먼트 트랙.
 *
 * 선택된 버튼에 클래스를 옮겨 다는 방식은 배경이 "툭" 나타난다. 대신 버튼들 뒤에
 * 알약 하나를 깔아 두고 그것만 translateX로 옮긴다 — 같은 요소가 이동하므로
 * iOS 세그먼트 컨트롤처럼 미끄러진다.
 *
 * 알약 폭이 곧 한 칸이라는 전제 위에서 translateX(index * 100%)가 성립하므로,
 * 트랙은 gap 없는 균등 그리드여야 한다(아래 --segment-count로 열 수를 맞춘다).
 * 버튼 자체의 라벨·아이콘·role은 호출부가 정한다 — 테마 선택은 radiogroup,
 * 보기 전환은 tablist라 여기서 못 박으면 둘 중 하나가 어긋난다.
 */
interface SegmentedControlProps {
  /** 트랙(레일) 클래스 — 호출부 모듈에서 배경·패딩·폰트를 정한다 */
  className: string;
  /** 버튼 개수 = 칸 수 */
  count: number;
  /** 지금 선택된 칸 (0부터) */
  activeIndex: number;
  role: 'radiogroup' | 'tablist';
  ariaLabel?: string;
  ariaLabelledBy?: string;
  children: ReactNode;
}

export function SegmentedControl({
  className,
  count,
  activeIndex,
  role,
  ariaLabel,
  ariaLabelledBy,
  children,
}: SegmentedControlProps) {
  return (
    <div
      className={`${styles.track} ${className}`}
      role={role}
      aria-label={ariaLabel}
      aria-labelledby={ariaLabelledBy}
      style={{ '--segment-count': count } as CSSProperties}
    >
      <span
        /* themeExempt: 테마 전환 300ms 동안 전역 규칙이 transform 트랜지션을
           덮어써 알약이 순간이동하는 것을 막는다 (global.css 참고) */
        className={`${styles.highlight} themeExempt`}
        aria-hidden
        style={{ transform: `translateX(${activeIndex * 100}%)` }}
      />
      {children}
    </div>
  );
}
