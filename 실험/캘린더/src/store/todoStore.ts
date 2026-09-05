import { v4 as uuid } from 'uuid';
import { create } from 'zustand';
import type { TodoItem } from '../types/todo';
import { getNow } from './clock';
import { loadTodos, saveTodosDebounced } from '../utils/storage';

/**
 * 할 일 스토어.
 *
 * calendarStore와 분리한 이유는 toolStore를 분리한 것과 같다 — 층위가 다르다.
 * calendarStore의 상태는 "달력을 어떻게 보고 있나 + 그 안에 무엇이 적혀 있나"이고,
 * 여기는 날짜 격자와 무관하게 살아가는 목록이다. 섞으면 goPrev/viewDate 같은
 * 달력 전용 개념이 할 일에도 의미가 있는 척하게 된다.
 */
interface TodoStore {
  todos: TodoItem[];
  addTodo: (title: string, dueDate: string) => void;
  toggleTodo: (id: string) => void;
  updateTodo: (id: string, patch: Partial<Pick<TodoItem, 'title' | 'dueDate'>>) => void;
  deleteTodo: (id: string) => void;
  replaceAllTodos: (todos: TodoItem[]) => void;
}

export const useTodoStore = create<TodoStore>((set) => ({
  todos: loadTodos(),

  addTodo: (title, dueDate) =>
    set((state) => {
      const trimmed = title.trim();
      if (!trimmed) return state;
      const now = getNow().toISOString();
      const todo: TodoItem = {
        id: uuid(),
        title: trimmed,
        dueDate,
        done: false,
        createdAt: now,
        updatedAt: now,
      };
      return { todos: [...state.todos, todo] };
    }),

  // 일정의 toggleComplete와 같은 결: 같은 걸 다시 누르면 해제된다
  toggleTodo: (id) =>
    set((state) => ({
      todos: state.todos.map((todo) =>
        todo.id === id ? { ...todo, done: !todo.done, updatedAt: getNow().toISOString() } : todo,
      ),
    })),

  updateTodo: (id, patch) =>
    set((state) => ({
      todos: state.todos.map((todo) =>
        todo.id === id ? { ...todo, ...patch, updatedAt: getNow().toISOString() } : todo,
      ),
    })),

  deleteTodo: (id) => set((state) => ({ todos: state.todos.filter((todo) => todo.id !== id) })),

  replaceAllTodos: (todos) => set({ todos }),
}));

useTodoStore.subscribe((state, prevState) => {
  if (state.todos !== prevState.todos) saveTodosDebounced(state.todos);
});
