import { useEffect } from 'react';
import { getTodayKey } from '../store/clock';
import { useTodoStore } from '../store/todoStore';
import { isOverdue, isPending } from '../types/todo';
import { isNotifyAvailable, notifyTodos } from '../utils/notify';

/**
 * 앱을 켤 때 남아 있는 할 일을 한 번 알린다. App에서 한 번만 부른다.
 *
 * 켠 직후 딱 한 번만 센다. 그 뒤에 할 일을 추가하거나 지워도 다시 알리지 않는다 —
 * 알림은 "켰을 때 잊은 게 있는지" 알려 주는 것이지, 작업 중에 끼어드는 장치가 아니다.
 * 같은 날 두 번째로 켰을 때 건너뛰는 판정은 메인 프로세스가 한다(날짜 기록 파일).
 *
 * Electron이 아니면(브라우저 개발 서버) 통째로 조용히 아무 일도 하지 않는다.
 */
export function useTodoNotice(): void {
  useEffect(() => {
    if (!isNotifyAvailable()) return;
    const todayKey = getTodayKey();
    const todos = useTodoStore.getState().todos;
    const pending = todos.filter((todo) => isPending(todo, todayKey));
    const overdue = pending.filter((todo) => isOverdue(todo, todayKey)).length;
    void notifyTodos({ today: pending.length - overdue, overdue });
  }, []);
}
