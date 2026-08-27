import { addDays } from 'date-fns';
import { Lock } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { getNow } from '../store/clock';
import { useCalendarStore } from '../store/calendarStore';
import {
  CATEGORIES,
  CATEGORY_COLORS,
  CATEGORY_LABELS,
  type CalendarEvent,
  type EventCategory,
  type EventInput,
} from '../types/event';
import { toDateKey } from '../utils/dateUtils';
import styles from './EventForm.module.css';

interface EventFormProps {
  dateKey: string;
  initial?: CalendarEvent;
  onDone: () => void;
}

export function EventForm({ dateKey, initial, onDone }: EventFormProps) {
  const addEvent = useCalendarStore((s) => s.addEvent);
  const updateEvent = useCalendarStore((s) => s.updateEvent);

  const [title, setTitle] = useState(initial?.title ?? '');
  const [time, setTime] = useState(initial?.time ?? '');
  const [memo, setMemo] = useState(initial?.memo ?? '');
  const [category, setCategory] = useState<EventCategory>(initial?.category ?? 'personal');
  const [customColor, setCustomColor] = useState(initial?.color ?? '#b8a7f0');
  const [projectTag, setProjectTag] = useState(initial?.projectTag ?? '');
  const [sealed, setSealed] = useState(Boolean(initial?.isSealed));
  const defaultSealUntil = toDateKey(addDays(getNow(), 7));
  const [sealedUntil, setSealedUntil] = useState(initial?.sealedUntil ?? defaultSealUntil);
  const [error, setError] = useState(false);

  const titleRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    titleRef.current?.focus();
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) {
      setError(true);
      titleRef.current?.focus();
      return;
    }
    const useSeal = sealed && sealedUntil > dateKey;
    const input: EventInput = {
      date: initial?.date ?? dateKey,
      title: trimmed,
      time: time || undefined,
      memo: memo.trim() || undefined,
      category,
      color: category === 'custom' ? customColor : undefined,
      projectTag: projectTag.trim() || undefined,
      isSealed: useSeal || undefined,
      sealedUntil: useSeal ? sealedUntil : undefined,
    };
    if (initial) updateEvent(initial.id, input);
    else addEvent(input);
    onDone();
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <input
        ref={titleRef}
        className={`${styles.titleInput} ${error ? styles.inputError : ''}`}
        placeholder="무슨 일정인가요? *"
        value={title}
        maxLength={80}
        onChange={(e) => {
          setTitle(e.target.value);
          if (error) setError(false);
        }}
      />
      {error && <p className={styles.errorText}>제목을 입력해 주세요</p>}

      <div className={styles.timeRow}>
        <label className={styles.timeLabel}>
          시간
          <input
            type="time"
            className={styles.timeInput}
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </label>
        {time && (
          <button type="button" className={styles.clearTime} onClick={() => setTime('')}>
            비우기
          </button>
        )}
        <span className={styles.hint}>비워 두면 하루 종일 일정</span>
      </div>

      <textarea
        className={styles.memoInput}
        placeholder="자세한 메모 (선택)"
        rows={3}
        value={memo}
        onChange={(e) => setMemo(e.target.value)}
      />

      <div className={styles.categoryRow} role="radiogroup" aria-label="카테고리">
        {CATEGORIES.map((cat) => (
          <button
            type="button"
            key={cat}
            role="radio"
            aria-checked={category === cat}
            className={`${styles.categoryPill} ${category === cat ? styles.categoryActive : ''}`}
            style={{ '--cat-color': CATEGORY_COLORS[cat] } as React.CSSProperties}
            onClick={() => setCategory(cat)}
          >
            <span className={styles.categoryDot} />
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {category === 'custom' && (
        <label className={styles.colorPicker}>
          라벨 색상
          <input type="color" value={customColor} onChange={(e) => setCustomColor(e.target.value)} />
          <span className={styles.colorValue}>{customColor}</span>
        </label>
      )}

      <label className={styles.tagField}>
        프로젝트 태그
        <input
          className={styles.tagInput}
          placeholder="예: 포트폴리오 (성좌 뷰에서 묶여요, 선택)"
          value={projectTag}
          maxLength={20}
          onChange={(e) => setProjectTag(e.target.value)}
        />
      </label>

      <div className={styles.sealBox}>
        <label className={styles.sealToggle}>
          <input type="checkbox" checked={sealed} onChange={(e) => setSealed(e.target.checked)} />
          <Lock size={14} aria-hidden />
          타임캡슐로 봉인하기
        </label>
        {sealed && (
          <label className={styles.sealDate}>
            개봉일
            <input
              type="date"
              value={sealedUntil}
              min={toDateKey(addDays(getNow(), 1))}
              onChange={(e) => setSealedUntil(e.target.value)}
            />
          </label>
        )}
      </div>
      {sealed && (
        <p className={styles.sealHint}>개봉일 전까지 제목과 내용이 흐리게 가려져요.</p>
      )}

      <div className={styles.actions}>
        <button type="button" className={styles.cancelButton} onClick={onDone}>
          취소
        </button>
        <button type="submit" className={styles.saveButton}>
          {initial ? '수정 저장' : '저장'}
        </button>
      </div>
    </form>
  );
}
