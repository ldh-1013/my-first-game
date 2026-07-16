import { moonPhase, moonPhaseName } from '../utils/moon';
import styles from './MoonPhase.module.css';

interface MoonPhaseProps {
  date: Date;
  size?: number;
}

/** 외부 라이브러리 없이 위상값으로 그린 달 아이콘 (은은한 장식용) */
export function MoonPhase({ date, size = 14 }: MoonPhaseProps) {
  const phase = moonPhase(date);
  const r = size / 2 - 0.5;
  const cos = Math.cos(phase * 2 * Math.PI);
  const rx = r * Math.abs(cos);
  const waxing = phase < 0.5;
  const bigSweep = waxing ? 1 : 0;
  const innerSweep = cos > 0 ? bigSweep : 1 - bigSweep;
  const litPath = `M0,${-r} A${r},${r} 0 0 ${bigSweep} 0,${r} A${rx.toFixed(2)},${r} 0 0 ${innerSweep} 0,${-r} Z`;

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
