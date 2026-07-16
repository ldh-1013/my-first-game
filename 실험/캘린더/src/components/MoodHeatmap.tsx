import { addDays, format, startOfWeek } from 'date-fns';
import { ko } from 'date-fns/locale';
import { useMemo } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { fromDateKey, toDateKey } from '../utils/dateUtils';
import { MOOD_LEVELS, MOOD_META, moodColor, moodLabel } from '../utils/mood';
import styles from './MoodHeatmap.module.css';

const WEEKS = 53;

interface Cell {
  key: string;
  inFuture: boolean;
  month: number;
}

export function MoodHeatmap() {
  const moods = useCalendarStore((s) => s.moods);
  const openDate = useCalendarStore((s) => s.openDate);
  const todayKey = useTodayKey();

  const { columns, monthLabels } = useMemo(() => {
    const today = fromDateKey(todayKey);
    // 이번 주 일요일 기준으로 53주 전까지 거슬러 올라간 시작점
    const gridStart = startOfWeek(addDays(startOfWeek(today), -(WEEKS - 1) * 7));
    const cols: Cell[][] = [];
    const labels: { col: number; text: string }[] = [];
    let lastMonth = -1;

    for (let w = 0; w < WEEKS; w++) {
      const week: Cell[] = [];
      for (let d = 0; d < 7; d++) {
        const date = addDays(gridStart, w * 7 + d);
        const key = toDateKey(date);
        week.push({ key, inFuture: key > todayKey, month: date.getMonth() });
        if (d === 0) {
          const month = date.getMonth();
          if (month !== lastMonth) {
            labels.push({ col: w, text: format(date, 'M월') });
            lastMonth = month;
          }
        }
      }
      cols.push(week);
    }
    return { columns: cols, monthLabels: labels };
  }, [todayKey]);

  const recordedCount = Object.keys(moods).length;

  return (
    <div className={styles.wrap}>
      <div className={styles.head}>
        <p className={styles.subtitle}>
          {recordedCount > 0
            ? `지금까지 ${recordedCount}일의 기분을 기록했어요`
            : '날짜를 열어 오늘의 기분을 남겨보세요. 각 칸은 하루예요.'}
        </p>
        <div className={styles.legend}>
          <span className={styles.legendText}>흐림</span>
          {[...MOOD_LEVELS].reverse().map((level) => (
            <span
              key={level}
              className={styles.legendDot}
              style={{ background: MOOD_META[level].color }}
              title={MOOD_META[level].label}
            />
          ))}
          <span className={styles.legendText}>좋음</span>
        </div>
      </div>

      <div className={styles.scroll}>
        <div className={styles.months}>
          {monthLabels.map((label) => (
            <span
              key={`${label.col}-${label.text}`}
              className={styles.monthLabel}
              style={{ gridColumn: label.col + 1 }}
            >
              {label.text}
            </span>
          ))}
        </div>
        <div className={styles.gridRow}>
          <div className={styles.weekdays}>
            <span>월</span>
            <span>수</span>
            <span>금</span>
          </div>
          <div className={styles.grid}>
            {columns.map((week, wi) => (
              <div key={wi} className={styles.week}>
                {week.map((cell) => {
                  if (cell.inFuture) {
                    return <div key={cell.key} className={styles.cellEmpty} aria-hidden />;
                  }
                  const level = moods[cell.key];
                  return (
                    <button
                      type="button"
                      key={cell.key}
                      className={styles.cell}
                      style={{ background: moodColor(level) }}
                      title={`${format(fromDateKey(cell.key), 'M월 d일 (EEE)', { locale: ko })} · ${moodLabel(level)}`}
                      onClick={() => openDate(cell.key)}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
