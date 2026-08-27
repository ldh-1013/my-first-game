import { useEffect } from 'react';
import { useCalendarStore } from '../store/calendarStore';
import { cacheBackup, getBackupStatus, isBackupAvailable, runBackup } from '../utils/backup';

/**
 * 자동 백업을 앱 수명에 붙인다. App에서 한 번만 부른다.
 *
 * 두 시점에만 디스크를 건드린다.
 *  1. 앱을 켰을 때 — 그날 백업이 아직 없으면 하나 만든다.
 *  2. 앱을 끌 때 — 메인 프로세스가 before-quit에서 그날 파일을 최신 내용으로 덮어쓴다.
 *
 * 데이터가 바뀔 때마다 파일을 쓰지는 않는다. 대신 바뀔 때마다 메인에 최신 스냅샷을
 * '맡겨 두기만' 해서(cacheBackup, 디스크 접근 없음) 종료 시점에 쓸 거리를 준비해 둔다.
 *
 * Electron이 아니면(브라우저 개발 서버) 이 훅은 통째로 조용히 아무 일도 하지 않는다.
 */
export function useAutoBackup(): void {
  // 1) 켤 때: 오늘 백업이 없으면 만든다
  useEffect(() => {
    if (!isBackupAvailable()) return;
    let cancelled = false;
    void (async () => {
      const status = await getBackupStatus();
      if (cancelled || !status || status.todayDone) return;
      const { events, moods } = useCalendarStore.getState();
      await runBackup(events, moods);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // 2) 데이터가 바뀌면 메인에 최신 스냅샷을 맡겨 둔다 (종료 시 쓰일 거리)
  useEffect(() => {
    if (!isBackupAvailable()) return;
    const push = () => {
      const { events, moods } = useCalendarStore.getState();
      cacheBackup(events, moods);
    };
    push(); // 아무것도 안 바뀐 채로 종료되는 경우까지 대비해 한 번 먼저
    return useCalendarStore.subscribe((state, prev) => {
      if (state.events !== prev.events || state.moods !== prev.moods) push();
    });
  }, []);
}
