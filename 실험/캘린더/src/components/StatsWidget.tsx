import { format } from 'date-fns';
import { ChartPie } from 'lucide-react';
import { useMemo } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import { CATEGORIES, CATEGORY_LABELS, type EventCategory } from '../types/event';
import styles from './StatsWidget.module.css';

// 도넛 지오메트리: 둘레가 정확히 100이 되는 반지름
const RADIUS = 15.9155;
const STROKE = 7;
const GAP = 2; // 세그먼트 사이 표면(흰색) 갭 — 색약 대비 보조 인코딩

const SEGMENT_COLORS: Record<EventCategory, string> = {
  work: 'var(--color-work)',
  personal: 'var(--color-personal)',
  important: 'var(--color-important)',
  idea: 'var(--color-idea)',
  custom: '#b8b5d1',
};

interface Segment {
  category: EventCategory;
  count: number;
  fraction: number;
}

export function StatsWidget() {
  const events = useCalendarStore((s) => s.events);
  const viewDate = useCalendarStore((s) => s.viewDate);

  const monthPrefix = format(viewDate, 'yyyy-MM');
  const { total, segments } = useMemo(() => {
    const monthEvents = events.filter((event) => event.date.startsWith(monthPrefix));
    const counts = new Map<EventCategory, number>();
    for (const event of monthEvents) {
      counts.set(event.category, (counts.get(event.category) ?? 0) + 1);
    }
    const totalCount = monthEvents.length;
    const segs: Segment[] = CATEGORIES.filter((cat) => (counts.get(cat) ?? 0) > 0).map((cat) => ({
      category: cat,
      count: counts.get(cat)!,
      fraction: (counts.get(cat) ?? 0) / totalCount,
    }));
    return { total: totalCount, segments: segs };
  }, [events, monthPrefix]);

  const gap = segments.length > 1 ? GAP : 0;
  let cumulative = 0;

  return (
    <section
      className={styles.widget}
      aria-label={`${format(viewDate, 'M월')} 통계: 총 일정 ${total}개`}
    >
      <h2 className={styles.widgetTitle}>
        <ChartPie size={16} aria-hidden /> {format(viewDate, 'M월')} 통계
      </h2>

      <div className={styles.content}>
        <svg viewBox="0 0 44 44" className={styles.donut} role="img" aria-hidden>
          {total === 0 ? (
            <circle
              cx="22"
              cy="22"
              r={RADIUS}
              fill="none"
              stroke="var(--color-border)"
              strokeWidth={STROKE}
            />
          ) : (
            segments.map((segment) => {
              const start = cumulative + gap / 2;
              const length = Math.max(segment.fraction * 100 - gap, 0.6);
              cumulative += segment.fraction * 100;
              return (
                <circle
                  key={segment.category}
                  cx="22"
                  cy="22"
                  r={RADIUS}
                  fill="none"
                  stroke={SEGMENT_COLORS[segment.category]}
                  strokeWidth={STROKE}
                  strokeDasharray={`${length} ${100 - length}`}
                  strokeDashoffset={25 - start}
                  className={styles.segment}
                >
                  <title>
                    {`${CATEGORY_LABELS[segment.category]} ${segment.count}개 (${Math.round(
                      segment.fraction * 100,
                    )}%)`}
                  </title>
                </circle>
              );
            })
          )}
          <text x="22" y="21.5" textAnchor="middle" className={styles.totalNumber}>
            {total}
          </text>
          <text x="22" y="28" textAnchor="middle" className={styles.totalCaption}>
            일정
          </text>
        </svg>

        <div className={styles.legend}>
          {total === 0 ? (
            <p className={styles.empty}>이번 달 일정이 없어요</p>
          ) : (
            segments.map((segment) => (
              <div key={segment.category} className={styles.legendRow}>
                <span
                  className={styles.legendDot}
                  style={{ background: SEGMENT_COLORS[segment.category] }}
                />
                <span className={styles.legendLabel}>{CATEGORY_LABELS[segment.category]}</span>
                <span className={styles.legendCount}>{segment.count}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
