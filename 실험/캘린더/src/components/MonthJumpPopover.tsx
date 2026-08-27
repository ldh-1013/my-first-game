import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import { useTodayKey } from '../store/clock';
import { fromDateKey } from '../utils/dateUtils';
import styles from './MonthJumpPopover.module.css';

const MONTH_LABELS = Array.from({ length: 12 }, (_, i) => `${i + 1}월`);

/** 화살표로 한 달씩 넘기는 대신 연/월을 직접 골라 점프하는 미니 달력. */
const MIN_YEAR = 1;
const MAX_YEAR = 9999;

interface Props {
  /** 툴바에 이미 떠 있던 제목 텍스트 — 그대로 트리거 버튼의 라벨이 된다 */
  title: string;
  /** 열려 있는 동안 App의 전역 ←/→ 단축키를 꺼 두기 위한 통지 */
  onOpenChange?: (open: boolean) => void;
}

export function MonthJumpPopover({ title, onOpenChange }: Props) {
  const viewDate = useCalendarStore((s) => s.viewDate);
  const goToMonth = useCalendarStore((s) => s.goToMonth);
  const todayKey = useTodayKey();
  const today = fromDateKey(todayKey);

  const [open, setOpen] = useState(false);
  const [year, setYear] = useState(() => viewDate.getFullYear());
  // null이면 연도를 숫자로 보여주는 상태, 문자열이면 그 자리에서 편집 중인 상태
  const [draft, setDraft] = useState<string | null>(null);

  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wasOpen = useRef(false);

  const viewYear = viewDate.getFullYear();
  const viewMonth = viewDate.getMonth();

  useEffect(() => {
    onOpenChange?.(open);
  }, [open, onOpenChange]);

  // 열 때마다 지금 보고 있는 연도에서 시작한다 (직전에 둘러보던 연도가 남아 있으면 헷갈린다)
  useEffect(() => {
    if (open) {
      setYear(viewYear);
      setDraft(null);
    }
  }, [open, viewYear]);

  // 열리면 포커스를 팝오버 안으로, 닫히면 트리거로 되돌린다
  useEffect(() => {
    if (open) panelRef.current?.focus();
    else if (wasOpen.current) triggerRef.current?.focus();
    wasOpen.current = open;
  }, [open]);

  useEffect(() => {
    if (draft !== null) inputRef.current?.select();
  }, [draft]);

  // 바깥 클릭 — SettingsMenu와 같은 방식
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  // Esc — 연도 편집 중이면 편집만 취소하고, 그 외에는 팝오버를 닫는다
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      if (draft !== null) setDraft(null);
      else setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, draft]);

  const clampYear = (value: number) => Math.min(MAX_YEAR, Math.max(MIN_YEAR, value));

  /** 빈 값·문자·범위 밖은 모두 확정하지 않고 원래 연도로 되돌린다 */
  const commitDraft = () => {
    if (draft === null) return;
    const parsed = Number(draft.trim());
    if (/^\d{1,4}$/.test(draft.trim()) && Number.isInteger(parsed) && parsed >= MIN_YEAR) {
      setYear(clampYear(parsed));
    }
    setDraft(null);
  };

  const pickMonth = (month: number) => {
    goToMonth(year, month);
    setOpen(false);
  };

  return (
    <div ref={rootRef} className={styles.root}>
      <h2 className={styles.title}>
        <button
          ref={triggerRef}
          type="button"
          className={styles.trigger}
          aria-haspopup="dialog"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          {title}
          <ChevronDown
            size={18}
            aria-hidden
            className={`${styles.chevron} ${open ? styles.chevronOpen : ''}`}
          />
        </button>
      </h2>

      {open && (
        <div
          ref={panelRef}
          className={styles.panel}
          role="dialog"
          aria-label="연월 이동"
          tabIndex={-1}
        >
          <div className={styles.yearRow}>
            <button
              type="button"
              className={styles.yearNav}
              aria-label="이전 연도"
              onClick={() => setYear((y) => clampYear(y - 1))}
            >
              <ChevronLeft size={16} />
            </button>

            {draft === null ? (
              <button
                type="button"
                className={styles.yearValue}
                aria-label={`연도 ${year}년, 눌러서 직접 입력`}
                onClick={() => setDraft(String(year))}
              >
                {year}
              </button>
            ) : (
              <input
                ref={inputRef}
                type="text"
                inputMode="numeric"
                className={styles.yearInput}
                aria-label="연도 직접 입력"
                value={draft}
                autoFocus
                onChange={(e) => setDraft(e.target.value)}
                onBlur={() => setDraft(null)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    commitDraft();
                  } else if (e.key === 'Escape') {
                    // 팝오버까지 닫지 않고 편집만 되돌린다
                    e.stopPropagation();
                    setDraft(null);
                  }
                }}
              />
            )}

            <button
              type="button"
              className={styles.yearNav}
              aria-label="다음 연도"
              onClick={() => setYear((y) => clampYear(y + 1))}
            >
              <ChevronRight size={16} />
            </button>
          </div>

          <div className={styles.months}>
            {MONTH_LABELS.map((label, month) => {
              const viewing = year === viewYear && month === viewMonth;
              const hasToday = year === today.getFullYear() && month === today.getMonth();
              return (
                <button
                  type="button"
                  key={label}
                  className={`${styles.monthButton} ${viewing ? styles.monthActive : ''}`}
                  aria-current={viewing ? 'true' : undefined}
                  aria-label={hasToday ? `${year}년 ${label} (오늘 포함)` : `${year}년 ${label}`}
                  onClick={() => pickMonth(month)}
                >
                  {label}
                  {/* 보고 있는 달은 채워서, 오늘이 든 달은 점으로 — 둘을 같은 세기로 칠하면 구분이 안 된다 */}
                  {hasToday && <span className={styles.todayDot} aria-hidden />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
