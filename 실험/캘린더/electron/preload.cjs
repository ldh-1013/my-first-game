const { contextBridge, ipcRenderer } = require('electron');

/**
 * 렌더러와 메인 프로세스 사이의 백업 전용 다리.
 *
 * 이 앱은 contextIsolation: true, nodeIntegration: false, sandbox: true라서
 * 렌더러(React)는 파일 시스템에 손을 댈 수 없다. 그래서 파일 쓰기는 전부 메인이 하고,
 * 여기서는 딱 필요한 네 가지 창구만 노출한다. (샌드박스 preload에서도
 * contextBridge와 ipcRenderer는 쓸 수 있지만 fs 같은 Node 모듈은 쓸 수 없다.)
 *
 * 브라우저(npm run dev)에는 preload가 없으므로 window.calendarBackup 자체가 없다.
 * 렌더러 쪽은 그 경우 조용히 아무것도 하지 않도록 되어 있다.
 */
/**
 * 진단 창구 — 렌더러에서 잡은 에러를 로그 파일로 넘기고, 그 폴더를 연다.
 * 화면이 텅 비어 버렸을 때 사용자가 유일하게 건네줄 수 있는 단서다.
 */
contextBridge.exposeInMainWorld('calendarDiagnostics', {
  report: (message) => ipcRenderer.send('diag:report', message),
  openLogFolder: () => ipcRenderer.invoke('diag:open-folder'),
});

/**
 * 할 일 알림 창구. 렌더러는 남은 개수만 넘기고, 문구와 '하루 한 번' 판정은 메인이 한다.
 */
contextBridge.exposeInMainWorld('calendarNotify', {
  todos: (counts) => ipcRenderer.invoke('notify:todos', counts),
});

/**
 * '컴퓨터 켤 때 할 일 확인' 창구. 등록 여부의 원천은 OS 로그인 항목이라,
 * 렌더러는 상태를 저장하지 않고 매번 물어본다.
 */
contextBridge.exposeInMainWorld('calendarStartup', {
  status: () => ipcRenderer.invoke('startup:status'),
  set: (enabled) => ipcRenderer.invoke('startup:set', enabled),
});

contextBridge.exposeInMainWorld('calendarBackup', {
  /** 지금 즉시 백업 파일을 쓴다 */
  run: (json) => ipcRenderer.invoke('backup:run', json),
  /** 최신 데이터를 메인에 맡겨 둔다. 종료 시점에 이 값으로 백업을 쓴다 (디스크에는 안 씀) */
  cache: (json) => ipcRenderer.send('backup:cache', json),
  /** 백업 폴더 경로, 마지막 백업 시각, 파일 개수 */
  status: () => ipcRenderer.invoke('backup:status'),
  /** 백업 폴더를 탐색기로 연다 */
  openFolder: () => ipcRenderer.invoke('backup:open-folder'),
});
