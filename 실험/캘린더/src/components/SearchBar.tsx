import { format } from 'date-fns';
import { Search } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import { useToolStore } from '../store/toolStore';
import { getEventColor, type CalendarEvent } from '../types/event';
import { compareEvents, fromDateKey } from '../utils/dateUtils';
import { isTypingTarget } from '../utils/keyboard';
import styles from './SearchBar.module.css';

function formatResultDate(event: CalendarEvent): string {
  const date = format(fromDateKey(event.date), 'M월 d일');
  return event.time ? `${date} · ${event.time}` : date;
}

export function SearchBar() {
  const events = useCalendarStore((s) => s.events);
  const openDate = useCalendarStore((s) => s.openDate);
  const closeTool = useToolStore((s) => s.closeTool);
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  // '/' 단축키로 검색창 포커스
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && !isTypingTarget(e.target)) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // 바깥 클릭 시 결과 닫기
  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setFocused(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, []);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return events
      .filter(
        (event) =>
          event.title.toLowerCase().includes(q) || event.memo?.toLowerCase().includes(q),
      )
      .sort((a, b) => a.date.localeCompare(b.date) || compareEvents(a, b))
      .slice(0, 12);
  }, [events, query]);

  const showDropdown = focused && query.trim().length > 0;

  const handleSelect = (event: CalendarEvent) => {
    // 헤더의 검색은 스톱워치/타이머 화면에서도 쓸 수 있다.
    // 그 상태로 상세 패널만 띄우면 뒤가 캘린더가 아니라 어색하므로 캘린더로 먼저 되돌린다.
    closeTool();
    openDate(event.date);
    setQuery('');
    setFocused(false);
  };

  return (
    <div ref={rootRef} className={styles.root}>
      <div className={styles.inputWrap}>
        <Search size={15} className={styles.icon} aria-hidden />
        <input
          ref={inputRef}
          className={styles.input}
          placeholder="일정 검색"
          value={query}
          onFocus={() => setFocused(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setFocused(true);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setFocused(false);
              inputRef.current?.blur();
            } else if (e.key === 'Enter' && results.length > 0) {
              handleSelect(results[0]);
              inputRef.current?.blur();
            }
          }}
          aria-label="일정 검색"
        />
        <kbd className={styles.kbd}>/</kbd>
      </div>
      {showDropdown && (
        <div className={styles.dropdown}>
          {results.length === 0 ? (
            <p className={styles.noResult}>'{query.trim()}' 검색 결과가 없어요</p>
          ) : (
            results.map((event) => (
              <button
                type="button"
                key={event.id}
                className={styles.result}
                onClick={() => handleSelect(event)}
              >
                <span className={styles.dot} style={{ background: getEventColor(event) }} />
                <span className={styles.resultTitle}>{event.title}</span>
                <span className={styles.resultDate}>{formatResultDate(event)}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
