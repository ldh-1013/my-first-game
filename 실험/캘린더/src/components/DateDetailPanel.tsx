import { differenceInCalendarDays } from 'date-fns';
import { Check, Lock, Pencil, Plus, Trash2, X } from 'lucide-react';
import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useCalendarStore } from '../store/calendarStore';
import { CATEGORY_LABELS, getEventColor, isLocked, type CalendarEvent } from '../types/event';
import { eventsOnDate, formatDayTitle, fromDateKey, groupEventsByDate } from '../utils/dateUtils';
import { getHoliday } from '../utils/holidays';
import { ConfirmDialog } from './ConfirmDialog';
import { EventForm } from './EventForm';
import { MoodPicker } from './MoodPicker';
import styles from './DateDetailPanel.module.css';

interface EventItemProps {
  event: CalendarEvent;
  locked: boolean;
  todayKey: string;
  /* 콜백은 항목별로 만들지 않고 id/이벤트를 인자로 받는다.
     렌더마다 새 화살표 함수를 넘기면 memo가 매번 깨져 아무 소용이 없다. */
  onToggleComplete: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (event: CalendarEvent) => void;
}

/** 목록의 한 줄. 부모(패널)가 다시 그려져도 자기 값이 그대로면 다시 그리지 않는다. */
const EventItem = memo(function EventItem({
  event,
  locked,
  todayKey,
  onToggleComplete,
  onEdit,
  onDelete,
}: EventItemProps) {

  const dDay = locked
    ? differenceInCalendarDays(fromDateKey(event.sealedUntil!), fromDateKey(todayKey))
    : 0;

  const done = Boolean(event.completed);

  return (
    <article
      className={`${styles.item} ${locked ? styles.itemLocked : ''} ${
        done ? styles.itemDone : ''
      }`}
      style={{ '--event-color': getEventColor(event) } as React.CSSProperties}
    >
      {/* 잠긴 타임캡슐은 수정과 마찬가지로 완료 체크도 막는다 */}
      {!locked && (
        <button
          type="button"
          className={`${styles.check} ${done ? styles.checkDone : ''}`}
          onClick={() => onToggleComplete(event.id)}
          aria-pressed={done}
          aria-label={done ? `${event.title} 완료 해제` : `${event.title} 완료로 표시`}
        >
          {done && <Check size={11} strokeWidth={3.5} aria-hidden />}
        </button>
      )}
      <div className={styles.itemBar} aria-hidden />
      <div className={styles.itemBody}>
        {locked ? (
          <>
            <div className={styles.lockedTop}>
              <Lock size={13} aria-hidden />
              <span className={styles.lockedBadge}>D-{Math.max(dDay, 1)}일 후 열람 가능</span>
            </div>
            <h4 className={`${styles.itemTitle} ${styles.blurred}`}>{event.title}</h4>
            {event.memo && <p className={`${styles.itemMemo} ${styles.blurred}`}>{event.memo}</p>}
          </>
        ) : (
          <>
            <div className={styles.itemTop}>
              {event.time && <span className={styles.itemTime}>{event.time}</span>}
              <span className={styles.itemCategory}>{CATEGORY_LABELS[event.category]}</span>
              {event.projectTag && <span className={styles.itemTag}>#{event.projectTag}</span>}
            </div>
            <h4 className={styles.itemTitle}>{event.title}</h4>
            {event.memo && <p className={styles.itemMemo}>{event.memo}</p>}
          </>
        )}
      </div>
      <div className={styles.itemActions}>
        {!locked && (
          <button type="button" aria-label="수정" onClick={() => onEdit(event.id)}>
            <Pencil size={15} />
          </button>
        )}
        <button
          type="button"
          aria-label="삭제"
          className={styles.deleteAction}
          onClick={() => onDelete(event)}
        >
          <Trash2 size={15} />
        </button>
      </div>
    </article>
  );
});

function EmptyState() {
  return (
    <div className={styles.empty}>
      <svg viewBox="0 0 120 100" width="120" height="100" aria-hidden>
        <rect x="22" y="22" width="76" height="64" rx="14" fill="var(--color-illust-paper)" />
        <rect x="22" y="22" width="76" height="20" rx="10" fill="var(--color-illust-band)" opacity="0.55" />
        <rect x="38" y="14" width="6" height="14" rx="3" fill="var(--color-illust-accent)" />
        <rect x="76" y="14" width="6" height="14" rx="3" fill="var(--color-illust-accent)" />
        <circle cx="45" cy="58" r="4" fill="var(--color-illust-accent)" />
        <circle cx="60" cy="58" r="4" fill="var(--color-illust-band)" />
        <circle cx="75" cy="58" r="4" fill="var(--color-illust-mint)" />
        <path
          d="M52 72 q8 7 16 0"
          stroke="var(--color-illust-line)"
          strokeWidth="2.4"
          strokeLinecap="round"
          fill="none"
        />
        <path d="M104 34 l2.2 5 5 2.2 -5 2.2 -2.2 5 -2.2 -5 -5 -2.2 5 -2.2 z" fill="var(--color-illust-pink)" />
        <path
          d="M12 54 l1.7 3.8 3.8 1.7 -3.8 1.7 -1.7 3.8 -1.7 -3.8 -3.8 -1.7 3.8 -1.7 z"
          fill="var(--color-illust-accent)"
        />
      </svg>
      <p className={styles.emptyTitle}>아직 일정이 없어요</p>
      <p className={styles.emptyHint}>위의 '새 메모' 버튼으로 오늘의 기록을 남겨보세요 ✨</p>
    </div>
  );
}

export function DateDetailPanel() {
  const selectedDate = useCalendarStore((s) => s.selectedDate);
  const selectDate = useCalendarStore((s) => s.selectDate);
  const events = useCalendarStore((s) => s.events);
  const deleteEvent = useCalendarStore((s) => s.deleteEvent);
  const toggleComplete = useCalendarStore((s) => s.toggleComplete);
  const todayKey = useTodayKey();

  const [displayDate, setDisplayDate] = useState<string | null>(null);
  const [isCreating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CalendarEvent | null>(null);

  useEffect(() => {
    if (selectedDate) {
      setDisplayDate(selectedDate);
      setCreating(false);
      setEditingId(null);
    }
  }, [selectedDate]);

  useEffect(() => {
    if (!selectedDate || deleteTarget) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') selectDate(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedDate, deleteTarget, selectDate]);

  const open = selectedDate !== null;
  const holiday = displayDate ? getHoliday(displayDate) : null;
  // 다른 화면들과 같은 그룹을 쓴다. 정렬은 groupEventsByDate가 이미 해 뒀다.
  const eventsByDate = useMemo(() => groupEventsByDate(events), [events]);
  const dayEvents = displayDate ? eventsOnDate(eventsByDate, displayDate) : [];
  const allDay = dayEvents.filter((event) => !event.time);
  const timed = dayEvents.filter((event) => event.time);

  // memo가 의미를 가지려면 이 참조들이 렌더마다 바뀌지 않아야 한다.
  // toggleComplete는 zustand 액션이라 이미 고정, 나머지는 setState만 쓰므로 의존성이 없다.
  const handleEdit = useCallback((id: string) => {
    setEditingId(id);
    setCreating(false);
  }, []);
  const handleDelete = useCallback((event: CalendarEvent) => setDeleteTarget(event), []);

  const renderItem = (event: CalendarEvent) => {
    const locked = isLocked(event, todayKey);
    return editingId === event.id && !locked ? (
      <EventForm
        key={event.id}
        dateKey={displayDate!}
        initial={event}
        onDone={() => setEditingId(null)}
      />
    ) : (
      <EventItem
        key={event.id}
        event={event}
        locked={locked}
        todayKey={todayKey}
        onToggleComplete={toggleComplete}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
    );
  };

  return (
    <>
      <div
        className={`${styles.backdrop} ${open ? styles.backdropOpen : ''}`}
        onClick={() => selectDate(null)}
        aria-hidden
      />
      <aside
        className={`${styles.panel} ${open ? styles.panelOpen : ''}`}
        aria-hidden={!open}
        aria-label="날짜 상세"
      >
        {displayDate && (
          <>
            <header className={styles.header}>
              <div>
                <h2 className={styles.dateTitle}>
                  {formatDayTitle(displayDate)}
                  {displayDate === todayKey && <span className={styles.todayBadge}>오늘</span>}
                  {holiday && (
                    <span
                      className={styles.holidayBadge}
                      title={
                        holiday.isSubstitute
                          ? `원래 공휴일 ${holiday.substituteFor}`
                          : '공휴일'
                      }
                    >
                      {holiday.name}
                      {holiday.isProjected ? ' (예상)' : ''}
                    </span>
                  )}
                </h2>
                <p className={styles.count}>
                  {dayEvents.length > 0 ? `일정 ${dayEvents.length}개` : ' '}
                </p>
              </div>
              <button
                type="button"
                className={styles.closeButton}
                aria-label="닫기"
                onClick={() => selectDate(null)}
              >
                <X size={18} />
              </button>
            </header>

            {/* 아직 오지 않은 날에는 기분을 기록할 수 없게 숨김 */}
            {displayDate <= todayKey && <MoodPicker dateKey={displayDate} />}

            {!isCreating && (
              <button
                type="button"
                className={styles.addButton}
                onClick={() => {
                  setCreating(true);
                  setEditingId(null);
                }}
              >
                <Plus size={16} /> 새 메모
              </button>
            )}
            {isCreating && <EventForm dateKey={displayDate} onDone={() => setCreating(false)} />}

            <div className={styles.list}>
              {allDay.length > 0 && (
                <section>
                  <h3 className={styles.sectionLabel}>하루 종일</h3>
                  <div className={styles.sectionItems}>{allDay.map(renderItem)}</div>
                </section>
              )}
              {timed.length > 0 && (
                <section>
                  <h3 className={styles.sectionLabel}>시간 일정</h3>
                  <div className={styles.sectionItems}>{timed.map(renderItem)}</div>
                </section>
              )}
              {dayEvents.length === 0 && !isCreating && <EmptyState />}
            </div>
          </>
        )}
      </aside>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="메모 삭제"
        message={
          deleteTarget
            ? `'${deleteTarget.title}' 메모를 삭제할까요? 삭제한 메모는 되돌릴 수 없어요.`
            : ''
        }
        confirmLabel="삭제"
        danger
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deleteEvent(deleteTarget.id);
          setDeleteTarget(null);
        }}
      />
    </>
  );
}
