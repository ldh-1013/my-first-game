import { format } from 'date-fns';
import { ListChecks, Plus } from 'lucide-react';
import { useMemo, useState, type FormEvent } from 'react';
import { useTodayKey } from '../hooks/useTodayKey';
import { useTodoStore } from '../store/todoStore';
import { compareTodos, isOverdue, isPending, type TodoItem } from '../types/todo';
import { fromDateKey } from '../utils/dateUtils';
import styles from './TodoWidget.module.css';

/**
 * 사이드바에 보이는 줄 수 상한.
 *
 * 밀린 항목은 완료하기 전까지 계속 남으므로, 그대로 두면 위젯 하나가 세로로 한없이
 * 길어져 아래 위젯들(1년 전 오늘·통계·도구)이 스크롤 밖으로 밀린다.
 * 5줄이면 다른 사이드바 카드(다가오는 일정 등)와 세로 균형이 맞고, 넘치는 몫은
 * CalendarGrid가 점을 자르고 '+N'을 붙이듯 한 줄로 접는다.
 */
const MAX_ROWS = 5;

/** '8/20 지남' — 며칠 밀렸는지보다 언제 마감이었는지가 바로 읽힌다 */
function overdueLabel(dueDate: string): string {
  return `${format(fromDateKey(dueDate), 'M/d')} 지남`;
}

interface TodoWidgetProps {
  /** '전체'와 '+N개 더'를 눌렀을 때 (전체 화면이 붙기 전에는 없다) */
  onOpenAll?: () => void;
}

export function TodoWidget({ onOpenAll }: TodoWidgetProps) {
  const todos = useTodoStore((s) => s.todos);
  const addTodo = useTodoStore((s) => s.addTodo);
  const toggleTodo = useTodoStore((s) => s.toggleTodo);
  const todayKey = useTodayKey();

  const [title, setTitle] = useState('');
  const [dueDate, setDueDate] = useState(todayKey);

  const pending = useMemo(
    () => todos.filter((todo) => isPending(todo, todayKey)).sort((a, b) => compareTodos(a, b, todayKey)),
    [todos, todayKey],
  );

  const shown = pending.slice(0, MAX_ROWS);
  const hidden = pending.length - shown.length;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    addTodo(title, /^\d{4}-\d{2}-\d{2}$/.test(dueDate) ? dueDate : todayKey);
    setTitle('');
    setDueDate(todayKey);
  };

  return (
    <section className={styles.widget} aria-label="오늘 할 일">
      <h2 className={styles.widgetTitle}>
        <ListChecks size={16} aria-hidden /> 오늘 할 일
        {onOpenAll && (
          <button type="button" className={styles.allButton} onClick={onOpenAll}>
            전체
          </button>
        )}
      </h2>

      {pending.length === 0 ? (
        <p className={styles.empty}>
          오늘 할 일이 없어요.
          <br />
          적어 두면 여기에 모여요 🌿
        </p>
      ) : (
        <ul className={styles.list}>
          {shown.map((todo) => (
            <TodoRow key={todo.id} todo={todo} todayKey={todayKey} onToggle={toggleTodo} />
          ))}
        </ul>
      )}

      {hidden > 0 && (
        <button type="button" className={styles.more} onClick={onOpenAll} disabled={!onOpenAll}>
          +{hidden}개 더
        </button>
      )}

      {/* 새 할 일 — EventForm의 시간 행과 같은 문법(제목 + 날짜 인풋) */}
      <form className={styles.addRow} onSubmit={handleSubmit}>
        <input
          className={styles.addInput}
          placeholder="할 일 추가"
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
    </section>
  );
}

function TodoRow({
  todo,
  todayKey,
  onToggle,
}: {
  todo: TodoItem;
  todayKey: string;
  onToggle: (id: string) => void;
}) {
  const overdue = isOverdue(todo, todayKey);
  return (
    <li className={styles.item}>
      <button
        type="button"
        className={styles.check}
        onClick={() => onToggle(todo.id)}
        aria-label={`${todo.title} 완료로 표시`}
      />
      <span className={styles.title}>{todo.title}</span>
      {overdue && <span className={styles.overdue}>{overdueLabel(todo.dueDate)}</span>}
    </li>
  );
}
