import { addMonths, addYears, format } from 'date-fns';
import { ChartColumn, ChevronLeft, ChevronRight } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import { useToolStore } from '../store/toolStore';
import { CATEGORY_COLORS, CATEGORY_LABELS } from '../types/event';
import { MOOD_META } from '../utils/mood';
import { busiestMonth, monthlyCounts, periodRecap } from '../utils/recap';
import { formatDayTitle } from '../utils/dateUtils';
import { SegmentedControl } from './SegmentedControl';
import { ToolScreen } from './ToolScreen';
import styles from './RecapScreen.module.css';

type RecapMode = 'month' | 'year';

const MODES: { mode: RecapMode; label: string }[] = [
  { mode: 'month', label: '월간' },
  { mode: 'year', label: '연간' },
];

const MONTH_LABELS = Array.from({ length: 12 }, (_, i) => `${i + 1}`);

/**
 * 지나간 한 달 또는 한 해를 돌아보는 화면.
 *
 * 세기만 하고 평가하지 않는다 — "많다/적다", "잘했다" 같은 문구를 넣지 않는 게
 * 이 앱의 톤이다(insight.ts 참고). 숫자와 막대만 담백하게 늘어놓는다.
 *
 * 기준 기간은 화면 로컬 상태다. 다만 App이 도구 화면들을 항상 마운트해 두므로,
 * 화면에 들어올 때마다 캘린더가 보고 있던 달로 맞춘다 — 8월을 보다 리캡을 열면
 * 8월이 나오고, 안에서 화살표로 옮긴 건 캘린더에 영향을 주지 않는다.
 */
export function RecapScreen() {
  const screen = useToolStore((s) => s.screen);
  const closeTool = useToolStore((s) => s.closeTool);
  const events = useCalendarStore((s) => s.events);
  const moods = useCalendarStore((s) => s.moods);
  const viewDate = useCalendarStore((s) => s.viewDate);
  const openDate = useCalendarStore((s) => s.openDate);

  const [mode, setMode] = useState<RecapMode>('month');
  const [anchor, setAnchor] = useState(() => viewDate);

  // 열 때마다 지금 보고 있는 달로 되돌린다 (나갔다 들어오면 리셋)
  useEffect(() => {
    if (screen === 'recap') setAnchor(viewDate);
    // viewDate는 의도적으로 의존성에서 뺀다 — 화면에 머무는 동안 캘린더가 바뀌어도 끌려가지 않는다
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screen]);

  const prefix = mode === 'month' ? format(anchor, 'yyyy-MM') : format(anchor, 'yyyy');
  const recap = useMemo(() => periodRecap(events, moods, prefix), [events, moods, prefix]);
  const perMonth = useMemo(
    () => (mode === 'year' ? monthlyCounts(events, anchor.getFullYear()) : []),
    [events, anchor, mode],
  );
  const peakMonth = mode === 'year' ? busiestMonth(perMonth) : null;
  const maxMonth = perMonth.length > 0 ? Math.max(...perMonth) : 0;

  const shift = (step: number) =>
    setAnchor((current) => (mode === 'month' ? addMonths(current, step) : addYears(current, step)));

  const periodLabel = mode === 'month' ? format(anchor, 'yyyy년 M월') : format(anchor, 'yyyy년');
  const topCategory = recap.categories.reduce<(typeof recap.categories)[number] | null>(
    (best, item) => (best === null || item.count > best.count ? item : best),
    null,
  );

  return (
    <ToolScreen title="리캡" icon={<ChartColumn size={18} aria-hidden />}>
      <div className={styles.wrap}>
        <SegmentedControl
          className={styles.modes}
          count={MODES.length}
          activeIndex={MODES.findIndex((m) => m.mode === mode)}
          role="tablist"
          ariaLabel="리캡 기간 전환"
        >
          {MODES.map((item) => (
            <button
              type="button"
              key={item.mode}
              role="tab"
              aria-selected={mode === item.mode}
              className={`${styles.modeButton} ${mode === item.mode ? styles.modeActive : ''}`}
              onClick={() => setMode(item.mode)}
            >
              {item.label}
            </button>
          ))}
        </SegmentedControl>

        <div className={styles.periodRow}>
          <button
            type="button"
            className={styles.navButton}
            aria-label={mode === 'month' ? '이전 달' : '이전 해'}
            onClick={() => shift(-1)}
          >
            <ChevronLeft size={18} />
          </button>
          <h3 className={styles.period}>{periodLabel}</h3>
          <button
            type="button"
            className={styles.navButton}
            aria-label={mode === 'month' ? '다음 달' : '다음 해'}
            onClick={() => shift(1)}
          >
            <ChevronRight size={18} />
          </button>
        </div>

        {recap.total === 0 && recap.moodDays === 0 ? (
          <p className={styles.empty}>이 기간에는 남긴 기록이 없어요</p>
        ) : (
          <div className={styles.cards}>
            <section className={styles.card}>
              <p className={styles.headline}>
                일정 <strong>{recap.total}</strong>개
                {recap.total > 0 && (
                  <span className={styles.headlineSub}>
                    완료 {recap.completed}개 · {Math.round(recap.completedRatio * 100)}%
                  </span>
                )}
              </p>
              {recap.total > 0 && (
                <div className={styles.meter} aria-hidden>
                  <div
                    className={styles.meterFill}
                    style={{ width: `${recap.completedRatio * 100}%` }}
                  />
                </div>
              )}
            </section>

            {mode === 'year' && (
              <section className={styles.card}>
                <h4 className={styles.cardTitle}>월별 일정</h4>
                <div className={styles.monthChart}>
                  {perMonth.map((count, index) => (
                    <div
                      key={MONTH_LABELS[index]}
                      className={styles.monthColumn}
                      title={`${index + 1}월 ${count}개`}
                    >
                      <div className={styles.track}>
                        <div
                          className={styles.bar}
                          style={{
                            // 높이와 진하기를 같은 값에서 뽑아 눈으로 본 크기와 수치가 어긋나지 않게
                            height: maxMonth > 0 ? `${(count / maxMonth) * 100}%` : '0%',
                            opacity: maxMonth > 0 ? 0.3 + (count / maxMonth) * 0.7 : 0,
                          }}
                          aria-hidden
                        />
                      </div>
                      <span className={styles.monthLabel}>{MONTH_LABELS[index]}</span>
                      <span className={styles.srOnly}>{`${index + 1}월 ${count}개`}</span>
                    </div>
                  ))}
                </div>
                {peakMonth !== null && (
                  <p className={styles.note}>
                    가장 많았던 달 · {peakMonth + 1}월 {perMonth[peakMonth]}개
                  </p>
                )}
              </section>
            )}

            {recap.categories.length > 0 && (
              <section className={styles.card}>
                <h4 className={styles.cardTitle}>카테고리</h4>
                <div className={styles.rows}>
                  {recap.categories.map((item) => (
                    <div key={item.category} className={styles.row}>
                      <span className={styles.rowLabel}>{CATEGORY_LABELS[item.category]}</span>
                      <div className={styles.rowTrack}>
                        <div
                          className={styles.rowFill}
                          style={{
                            width: `${item.fraction * 100}%`,
                            background: CATEGORY_COLORS[item.category],
                          }}
                        />
                      </div>
                      <span className={styles.rowValue}>{item.count}</span>
                    </div>
                  ))}
                </div>
                {topCategory && (
                  <p className={styles.note}>
                    가장 많이 쓴 카테고리 · {CATEGORY_LABELS[topCategory.category]}
                  </p>
                )}
              </section>
            )}

            {mode === 'month' && recap.busiestDay && (
              <section className={styles.card}>
                <h4 className={styles.cardTitle}>가장 바빴던 날</h4>
                <button
                  type="button"
                  className={styles.dayButton}
                  onClick={() => {
                    openDate(recap.busiestDay!.dateKey);
                    closeTool();
                  }}
                >
                  <span>{formatDayTitle(recap.busiestDay.dateKey)}</span>
                  <span className={styles.dayCount}>{recap.busiestDay.count}개</span>
                </button>
              </section>
            )}

            {recap.moodDays > 0 && (
              <section className={styles.card}>
                <h4 className={styles.cardTitle}>기분</h4>
                <div className={styles.moodBar} aria-hidden>
                  {recap.moods.map((item) => (
                    <span
                      key={item.level}
                      className={styles.moodPart}
                      style={{ width: `${item.fraction * 100}%`, background: MOOD_META[item.level].color }}
                      title={`${MOOD_META[item.level].label} ${item.count}일`}
                    />
                  ))}
                </div>
                <div className={styles.moodLegend}>
                  {recap.moods.map((item) => (
                    <span key={item.level} className={styles.moodItem}>
                      <span
                        className={styles.moodDot}
                        style={{ background: MOOD_META[item.level].color }}
                        aria-hidden
                      />
                      {MOOD_META[item.level].label} {item.count}일
                    </span>
                  ))}
                </div>
                <p className={styles.note}>기분을 남긴 날 {recap.moodDays}일</p>
              </section>
            )}

            {(recap.sealedCount > 0 || recap.unsealedCount > 0) && (
              <section className={styles.card}>
                <h4 className={styles.cardTitle}>타임캡슐</h4>
                <p className={styles.note}>
                  {recap.sealedCount > 0 && `봉인 ${recap.sealedCount}개`}
                  {recap.sealedCount > 0 && recap.unsealedCount > 0 && ' · '}
                  {recap.unsealedCount > 0 && `개봉일 도래 ${recap.unsealedCount}개`}
                </p>
              </section>
            )}
          </div>
        )}
      </div>
    </ToolScreen>
  );
}
