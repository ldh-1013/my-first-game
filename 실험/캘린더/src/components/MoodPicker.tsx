import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { MOOD_LEVELS, MOOD_META, moodLabel } from '../utils/mood';
import styles from './MoodPicker.module.css';

interface MoodPickerProps {
  dateKey: string;
}

export function MoodPicker({ dateKey }: MoodPickerProps) {
  const current = useCalendarStore((s) => s.moods[dateKey]);
  const setMood = useCalendarStore((s) => s.setMood);
  const todayKey = useTodayKey();
  // 열려 있는 날짜에 기록되므로, 오늘이 아닌 날에는 라벨로 명확히 구분
  const label = dateKey === todayKey ? '오늘 기분' : '이날의 기분';

  return (
    <div className={styles.wrap}>
      <span className={styles.label}>{label}</span>
      <div className={styles.swatches} role="radiogroup" aria-label={label}>
        {MOOD_LEVELS.map((level) => {
          const active = current === level;
          return (
            <button
              type="button"
              key={level}
              role="radio"
              aria-checked={active}
              className={`${styles.swatch} ${active ? styles.active : ''}`}
              style={{ background: MOOD_META[level].color }}
              title={MOOD_META[level].label}
              aria-label={MOOD_META[level].label}
              onClick={() => setMood(dateKey, level)}
            />
          );
        })}
      </div>
      {current && <span className={styles.currentLabel}>{moodLabel(current)}</span>}
    </div>
  );
}
