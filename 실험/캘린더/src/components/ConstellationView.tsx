import { differenceInCalendarDays, format } from 'date-fns';
import { Stars } from 'lucide-react';
import { useMemo } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import { isLocked, tagOf, type CalendarEvent } from '../types/event';
import { compareEvents, fromDateKey } from '../utils/dateUtils';
import { useTodayKey } from '../hooks/useTodayKey';
import styles from './ConstellationView.module.css';

// 파스텔 팔레트 안에서만 순환 (새 채도 색 만들지 않음)
const TAG_PALETTE = [
  '#7C9EFF',
  '#C7B9FF',
  '#A5C4FF',
  '#9EE7C7',
  '#FF9EB5',
  '#B8A7F0',
  '#8FD8E6',
  '#F5B8D0',
];

const LANE_HEIGHT = 74;
const MARGIN_TOP = 44;
const MARGIN_LEFT = 128;
const MARGIN_RIGHT = 48;

interface Node {
  event: CalendarEvent;
  x: number;
  y: number;
  r: number;
  locked: boolean;
}

interface Lane {
  tag: string;
  color: string;
  y: number;
  nodes: Node[];
}

export function ConstellationView() {
  const events = useCalendarStore((s) => s.events);
  const openDate = useCalendarStore((s) => s.openDate);
  const todayKey = useTodayKey();

  const layout = useMemo(() => {
    if (events.length === 0) return null;

    // 태그별 그룹화 + 시간순 정렬
    const groups = new Map<string, CalendarEvent[]>();
    for (const event of events) {
      const tag = tagOf(event);
      const list = groups.get(tag);
      if (list) list.push(event);
      else groups.set(tag, [event]);
    }

    const sortedDates = events.map((e) => e.date).sort();
    const minDate = fromDateKey(sortedDates[0]);
    const maxDate = fromDateKey(sortedDates[sortedDates.length - 1]);
    const rangeDays = Math.max(differenceInCalendarDays(maxDate, minDate), 1);
    const pxPerDay = rangeDays > 180 ? 6 : rangeDays > 90 ? 11 : 22;
    const innerWidth = rangeDays * pxPerDay;

    const xOf = (dateKey: string) =>
      MARGIN_LEFT + differenceInCalendarDays(fromDateKey(dateKey), minDate) * pxPerDay;

    // 첫 일정이 이른 태그를 위 레인에 배치, 같으면 이름순
    const firstDateOf = (tag: string) =>
      groups.get(tag)!.reduce((min, e) => (e.date < min ? e.date : min), '9999-99-99');
    const tags = [...groups.keys()].sort(
      (a, b) => firstDateOf(a).localeCompare(firstDateOf(b)) || a.localeCompare(b),
    );

    const lanes: Lane[] = tags.map((tag, laneIndex) => {
      const list = [...groups.get(tag)!].sort(compareEvents);
      const y = MARGIN_TOP + laneIndex * LANE_HEIGHT + LANE_HEIGHT / 2;
      const color = TAG_PALETTE[laneIndex % TAG_PALETTE.length];
      const nodes: Node[] = list.map((event) => {
        const memoLen = (event.memo?.length ?? 0) + event.title.length;
        const r = Math.max(6, Math.min(16, 6 + memoLen / 22));
        return { event, x: xOf(event.date), y, r, locked: isLocked(event, todayKey) };
      });
      return { tag, color, y, nodes };
    });

    // 월 눈금
    const monthTicks: { x: number; label: string }[] = [];
    let cursor = new Date(minDate.getFullYear(), minDate.getMonth(), 1);
    while (cursor <= maxDate) {
      monthTicks.push({
        x: MARGIN_LEFT + differenceInCalendarDays(cursor, minDate) * pxPerDay,
        label: format(cursor, 'yyyy.M'),
      });
      cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    }

    const width = MARGIN_LEFT + innerWidth + MARGIN_RIGHT;
    const height = MARGIN_TOP + lanes.length * LANE_HEIGHT + 24;
    return { lanes, monthTicks, width, height };
  }, [events, todayKey]);

  if (!layout) {
    return (
      <div className={styles.empty}>
        <Stars size={40} aria-hidden />
        <p className={styles.emptyTitle}>아직 이어질 별이 없어요</p>
        <p className={styles.emptyHint}>
          일정에 같은 카테고리나 프로젝트 태그를 달면 별자리처럼 이어져요 ✨
        </p>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <p className={styles.hint}>
        같은 태그의 일정이 시간 순서대로 이어집니다. 점을 누르면 그날로 이동해요.
      </p>
      <div className={styles.scroll}>
        <svg
          width={layout.width}
          height={layout.height}
          className={styles.canvas}
          role="img"
          aria-label="일정 성좌"
        >
          {/* 월 눈금 */}
          {layout.monthTicks.map((tick, i) => (
            <g key={i}>
              <line
                x1={tick.x}
                y1={MARGIN_TOP - 16}
                x2={tick.x}
                y2={layout.height - 12}
                className={styles.tickLine}
              />
              <text x={tick.x + 4} y={MARGIN_TOP - 22} className={styles.tickLabel}>
                {tick.label}
              </text>
            </g>
          ))}

          {layout.lanes.map((lane) => (
            <g key={lane.tag}>
              {/* 레인 라벨 */}
              <text x={16} y={lane.y + 4} className={styles.laneLabel} style={{ fill: lane.color }}>
                {lane.tag.length > 10 ? `${lane.tag.slice(0, 9)}…` : lane.tag}
              </text>

              {/* 연결 곡선 */}
              {lane.nodes.slice(1).map((node, i) => {
                const prev = lane.nodes[i];
                const midX = (prev.x + node.x) / 2;
                const d = `M ${prev.x} ${prev.y} C ${midX} ${prev.y - 18}, ${midX} ${node.y - 18}, ${node.x} ${node.y}`;
                return <path key={node.event.id} d={d} stroke={lane.color} className={styles.link} />;
              })}

              {/* 노드 */}
              {lane.nodes.map((node) => (
                <g
                  key={node.event.id}
                  className={styles.node}
                  onClick={() => openDate(node.event.date)}
                  role="button"
                  aria-label={`${format(fromDateKey(node.event.date), 'M월 d일')} ${node.locked ? '봉인된 일정' : node.event.title}`}
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.r}
                    fill={node.locked ? 'var(--color-border)' : lane.color}
                    className={styles.nodeCircle}
                  />
                  <circle cx={node.x} cy={node.y} r={node.r + 5} className={styles.nodeHit} />
                  <text x={node.x} y={node.y - node.r - 6} className={styles.nodeLabel}>
                    {node.locked ? '🔒' : node.event.title.length > 8 ? `${node.event.title.slice(0, 7)}…` : node.event.title}
                  </text>
                </g>
              ))}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}
