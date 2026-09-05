/**
 * 할 일.
 *
 * CalendarEvent와 필드가 겹치지만 성격이 다르다. 일정은 "몇 시에 무엇을 한다"이고
 * 할 일은 "언제까지 끝낸다"라, 시간·카테고리·타임캡슐 같은 개념이 아예 필요 없다.
 * 억지로 한 타입에 담으면 어느 쪽에도 안 맞는 필드가 계속 늘어난다.
 */
export interface TodoItem {
  id: string;
  title: string;
  /** 'YYYY-MM-DD' — 이 날짜까지 끝내야 하는 할 일 */
  dueDate: string;
  done: boolean;
  createdAt: string;
  updatedAt: string;
}

/** 오늘까지(=오늘 마감 + 기한 지남) 남아 있는 할 일인지 */
export function isPending(todo: TodoItem, todayKey: string): boolean {
  return !todo.done && todo.dueDate <= todayKey;
}

/** 기한이 이미 지난 미완료 할 일인지 */
export function isOverdue(todo: TodoItem, todayKey: string): boolean {
  return !todo.done && todo.dueDate < todayKey;
}

/**
 * 사이드바 위젯의 정렬.
 *
 * 오늘 마감을 먼저, 밀린 것을 뒤에 둔다. 위젯 이름 그대로 '오늘 할 일'을 보는
 * 자리라, 밀린 게 쌓였다는 이유로 정작 오늘 것이 잘려 안 보이면 위젯이 제 일을
 * 못 한다. 밀린 항목은 날짜 배지와 '+N개 더'로 존재를 알리고, 자세한 건 전체 화면에서 본다.
 * 같은 묶음 안에서는 마감이 이른 것부터(밀린 것은 오래된 것부터) 본다.
 */
export function compareTodos(a: TodoItem, b: TodoItem, todayKey: string): number {
  const aOverdue = a.dueDate < todayKey;
  const bOverdue = b.dueDate < todayKey;
  if (aOverdue !== bOverdue) return aOverdue ? 1 : -1;
  return a.dueDate.localeCompare(b.dueDate) || a.createdAt.localeCompare(b.createdAt);
}
