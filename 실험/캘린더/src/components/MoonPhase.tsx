import { moonPhase, moonPhaseName } from '../utils/moon';
import styles from './MoonPhase.module.css';

interface MoonPhaseProps {
  date: Date;
  size?: number;
}

/**
 * 외부 라이브러리 없이 위상값으로 그린 달 아이콘 (은은한 장식용).
 *
 * 밝은 부분은 두 곡선으로 둘러싸인 영역이다.
 *  - 바깥쪽: 밝은 쪽 반원 (북반구 기준 차오를 때 오른쪽, 기울 때 왼쪽)
 *  - 안쪽: 명암 경계선(터미네이터). 원을 비스듬히 본 것이라 가로 반지름이
 *    r·|cos(위상각)|인 반타원이 되고, 상현/하현에서는 0이 되어 직선이 된다.
 * 터미네이터가 어느 쪽으로 부푸느냐가 초승달(가늘게)과 볼록달(도톰하게)을 가른다.
 */
export function MoonPhase({ date, size = 14 }: MoonPhaseProps) {
  // 달력 칸은 '그 날 하루'를 뜻하므로 자정이 아니라 정오를 대표 시각으로 삼는다.
  const noon = new Date(date);
  noon.setHours(12, 0, 0, 0);

  const phase = moonPhase(noon);
  const r = size / 2 - 0.5;

  const cos = Math.cos(phase * 2 * Math.PI);
  const rx = r * Math.abs(cos);
  const waxing = phase < 0.5;

  // 바깥 반원: 위에서 아래로 그릴 때 sweep 1이면 오른쪽, 0이면 왼쪽으로 돈다.
  const outerSweep = waxing ? 1 : 0;
  // 터미네이터는 밝은 쪽(차오름=오른쪽)과 cos 부호를 함께 따른다.
  // cos > 0이면 아직 반달이 안 된 크레센트라 밝은 쪽으로 파고들고,
  // cos < 0이면 반달을 넘긴 볼록달이라 반대쪽으로 부푼다.
  const bulgesRight = waxing === cos >= 0;
  // 아래에서 위로 되돌아오는 방향이라 sweep 의미가 바깥 반원과 반대다.
  const innerSweep = bulgesRight ? 0 : 1;

  const litPath = `M0,${-r} A${r},${r} 0 0 ${outerSweep} 0,${r} A${rx.toFixed(2)},${r} 0 0 ${innerSweep} 0,${-r} Z`;

  return (
    <svg
      className={styles.moon}
      width={size}
      height={size}
      viewBox={`${-size / 2} ${-size / 2} ${size} ${size}`}
      role="img"
      aria-label={`${moonPhaseName(phase)}`}
    >
      <circle r={r} fill="none" stroke="var(--color-secondary)" strokeWidth="0.9" />
      <path d={litPath} fill="var(--color-primary)" />
    </svg>
  );
}
