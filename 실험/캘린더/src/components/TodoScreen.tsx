import { format } from 'date-fns';
import { ListChecks, Plus, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useTodoStore } from '../store/todoStore';
import { isOverdue, type TodoItem } from '../types/todo';
import { fromDateKey } from '../utils/dateUtils';
import { SegmentedControl } from './SegmentedControl';
import { ToolScreen } from './ToolScreen';
import styles from './TodoScreen.module.css';

type Filter = 'open' | 'done' | 'all';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'open', label: '남은 것' },
  { value: 'done', label: '완료' },
  { value: 'all', label: '전체' },
];

/**
 * '9/2 지남 · 오늘 · 내일 · 9월 12일' — 목록에서 날짜를 눈으로 훑을 수 있게.
 * 끝낸 일에는 '지남'을 붙이지 않는다. 이미 한 일에 지났다고 말할 이유가 없다.
 */
function dueLabel(todo: TodoItem, todayKey: string): string {
  const dueDate = todo.dueDate;
  if (dueDate < todayKey) {
    return todo.done ? format(fromDateKey(dueDate), 'M월 d일') : `${format(fromDateKey(dueDate), 'M/d')} 지남`;
  }
  if (dueDate === todayKey) return '오늘';
  const diff = (fromDateKey(dueDate).getTime() - fromDateKey(todayKey).getTime()) / 86_400_000;
  if (diff === 1) return '내일';
  return format(fromDateKey(dueDate), 'M월 d일');
}

/**
 * 할 일 전체 화면.
 *
 * 사이드바 위젯은 '오늘 남은 것'만 5줄까지 보여주므로, 미래 항목과 끝낸 항목은
 * 여기서 본다. 다른 도구 화면들처럼 ToolScreen 껍데기를 써서 뒤로가기·Esc가 같다.
 */
export function TodoScreen() {
  const todos = useTodoStore((s) => s.todos);
  const addTodo = useTodoStore((s) => s.addTodo);
  const toggleTodo = useTodoStore((s) => s.toggleTodo);
  const updateTodo = useTodoStore((s) => s.updateTodo);
  const deleteTodo = useTodoStore((s) => s.deleteTodo);
  const todayKey = useTodayKey();

  const [filter, setFilter] = useState<Filter>('open');
  const [title, setTitle] = useState('');
  const [dueDate, setDueDate] = useState(todayKey);

  const rows = useMemo(() => {
    const visible = todos.filter((todo) =>
      filter === 'all' ? true : filter === 'open' ? !todo.done : todo.done,
    );
    // 마감이 이른 것부터. 완료 목록도 같은 기준이라 눈이 옮겨 다니지 않는다.
    return visible.sort(
      (a, b) => a.dueDate.localeCompare(b.dueDate) || a.createdAt.localeCompare(b.createdAt),
    );
  }, [todos, filter]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    addTodo(title, /^\d{4}-\d{2}-\d{2}$/.test(dueDate) ? dueDate : todayKey);
    setTitle('');
  };

  return (
    <ToolScreen title="할 일" icon={<ListChecks size={18} aria-hidden />}>
      <div className={styles.wrap}>
        <SegmentedControl
          className={styles.filters}
          count={FILTERS.length}
          activeIndex={FILTERS.findIndex((f) => f.value === filter)}
          role="tablist"
          ariaLabel="할 일 목록 필터"
        >
          {FILTERS.map((item) => (
            <button
              type="button"
              key={item.value}
              role="tab"
              aria-selected={filter === item.value}
              className={`${styles.filterButton} ${filter === item.value ? styles.filterActive : ''}`}
              onClick={() => setFilter(item.value)}
            >
              {item.label}
            </button>
          ))}
        </SegmentedControl>

        <form className={styles.addRow} onSubmit={handleSubmit}>
          <input
            className={styles.addInput}
            placeholder="새 할 일"
            value={title}
            maxLength={80}
            onChange={(e) => setTitle(e.target.value)}
            aria-label="할 일 제목"
          />
          <input
            type="date"
            className={styles.addDate}
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            aria-label="마감 날짜"
          />
          <button type="submit" className={styles.addButton} aria-label="할 일 추가">
            <Plus size={16} />
          </button>
        </form>

        {rows.length === 0 ? (
          <p className={styles.empty}>
            {filter === 'done' ? '아직 끝낸 할 일이 없어요' : '남아 있는 할 일이 없어요'}
          </p>
        ) : (
          <ul className={styles.list}>
            {rows.map((todo) => (
              <TodoRow
                key={todo.id}
                todo={todo}
                todayKey={todayKey}
                onToggle={toggleTodo}
                onUpdate={updateTodo}
                onDelete={deleteTodo}
              />
            ))}
          </ul>
        )}
      </div>
    </ToolScreen>
  );
}

interface TodoRowProps {
  todo: TodoItem;
  todayKey: string;
  onToggle: (id: string) => void;
  onUpdate: (id: string, patch: Partial<Pick<TodoItem, 'title' | 'dueDate'>>) => void;
  onDelete: (id: string) => void;
}

function TodoRow({ todo, todayKey, onToggle, onUpdate, onDelete }: TodoRowProps) {
  // 제목을 눌러 그 자리에서 고친다 — MonthJumpPopover의 연도 입력과 같은 방식.
  // 할 일 한 줄을 고치려고 별도 폼을 여는 건 과하다.
  const [draft, setDraft] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (draft !== null) inputRef.current?.select();
  }, [draft]);

  const commit = () => {
    if (draft === null) return;
    const trimmed = draft.trim();
    if (trimmed && trimmed !== todo.title) onUpdate(todo.id, { title: trimmed });
    setDraft(null);
  };

  return (
    <li className={`${styles.item} ${todo.done ? styles.itemDone : ''}`}>
      <button
        type="button"
        className={`${styles.check} ${todo.done ? styles.checkDone : ''}`}
        onClick={() => onToggle(todo.id)}
        aria-pressed={todo.done}
        aria-label={todo.done ? `${todo.title} 완료 해제` : `${todo.title} 완료로 표시`}
      />

      {draft === null ? (
        <button
          type="button"
          className={styles.title}
          onClick={() => setDraft(todo.title)}
          aria-label={`${todo.title} 제목 수정`}
        >
          {todo.title}
        </button>
      ) : (
        <input
          ref={inputRef}
          className={styles.titleInput}
          value={draft}
          maxLength={80}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => setDraft(null)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              commit();
            } else if (e.key === 'Escape') {
              e.stopPropagation(); // 화면까지 닫히지 않게 (Esc는 캘린더 복귀 단축키다)
              setDraft(null);
            }
          }}
          aria-label="할 일 제목"
        />
      )}

      <span className={`${styles.due} ${isOverdue(todo, todayKey) ? styles.dueOverdue : ''}`}>
        {dueLabel(todo, todayKey)}
      </span>

      <input
        type="date"
        className={styles.dateInput}
        value={todo.dueDate}
        onChange={(e) => {
          if (/^\d{4}-\d{2}-\d{2}$/.test(e.target.value)) {
            onUpdate(todo.id, { dueDate: e.target.value });
          }
        }}
        aria-label={`${todo.title} 마감 날짜`}
      />

      {/* 한 줄짜리라 확인 모달 없이 바로 지운다. 대신 버튼은 이 줄에 올렸을 때만 드러난다 */}
      <button
        type="button"
        className={styles.delete}
        onClick={() => onDelete(todo.id)}
        aria-label={`${todo.title} 삭제`}
      >
        <Trash2 size={15} />
      </button>
    </li>
  );
}
