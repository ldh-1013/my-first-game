import { useEffect, useMemo, useState } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { loadCelebratedIds, saveCelebratedIds } from '../utils/storage';
import styles from './Celebration.module.css';

const SPARKLE_COUNT = 18;
const COLORS = [
  'var(--color-tag-1)',
  'var(--color-tag-2)',
  'var(--color-tag-4)',
  'var(--color-tag-5)',
  'var(--color-tag-3)',
];

/**
 * 봉인 해제일이 지난 타임캡슐을 페이지 로드 시 감지해
 * 딱 한 번 반짝임 연출을 보여준다 (이미 축하한 id는 localStorage에 기록).
 */
export function Celebration() {
  const events = useCalendarStore((s) => s.events);
  const todayKey = useTodayKey();
  const [active, setActive] = useState<{ id: number; title: string } | null>(null);

  useEffect(() => {
    const celebrated = new Set(loadCelebratedIds());
    const revealed = events.filter(
      (e) => e.isSealed && e.sealedUntil && todayKey >= e.sealedUntil && !celebrated.has(e.id),
    );
    if (revealed.length === 0) return;

    for (const e of revealed) celebrated.add(e.id);
    saveCelebratedIds([...celebrated]);
    setActive({ id: Date.now(), title: revealed[0].title });

    const timer = window.setTimeout(() => setActive(null), 1600);
    return () => window.clearTimeout(timer);
  }, [events, todayKey]);

  const sparkles = useMemo(
    () =>
      Array.from({ length: SPARKLE_COUNT }, (_, i) => ({
        angle: (i / SPARKLE_COUNT) * 360 + Math.random() * 12,
        distance: 90 + Math.random() * 140,
        delay: Math.random() * 0.2,
        color: COLORS[i % COLORS.length],
        size: 6 + Math.random() * 8,
      })),
    [active?.id],
  );

  if (!active) return null;

  return (
    <div className={styles.overlay} aria-hidden>
      <div className={styles.burst}>
        {sparkles.map((s, i) => (
          <span
            key={i}
            className={styles.sparkle}
            style={
              {
                '--angle': `${s.angle}deg`,
                '--distance': `${s.distance}px`,
                '--delay': `${s.delay}s`,
                '--size': `${s.size}px`,
                background: s.color,
              } as React.CSSProperties
            }
          />
        ))}
        <div className={styles.card}>
          <span className={styles.emoji}>🎉</span>
          <p className={styles.title}>타임캡슐이 열렸어요</p>
          <p className={styles.sub}>“{active.title}”</p>
        </div>
      </div>
    </div>
  );
}
