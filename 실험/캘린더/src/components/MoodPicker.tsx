import { useCalendarStore } from '../store/calendarStore';
import { MOOD_LEVELS, MOOD_META, moodLabel } from '../utils/mood';
import styles from './MoodPicker.module.css';

interface MoodPickerProps {
  dateKey: string;
}

export function MoodPicker({ dateKey }: MoodPickerProps) {
  const current = useCalendarStore((s) => s.moods[dateKey]);
  const setMood = useCalendarStore((s) => s.setMood);

  return (
    <div className={styles.wrap}>
      <span className={styles.label}>오늘 기분</span>
      <div className={styles.swatches} role="radiogroup" aria-label="오늘 기분">
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
