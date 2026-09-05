const { app, BrowserWindow, Menu, Notification, shell, nativeTheme, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

/* ===========================================================================
   오류 로그

   "창은 뜨는데 안이 텅 비어 있다"는 신고가 들어오면, 그 컴퓨터에서 확인할 수 있는
   단서가 하나도 없다. 렌더러 콘솔은 볼 수 없고 재현도 안 되기 때문이다.
   그래서 실패는 전부 userData 폴더의 파일 하나에 append 해 둔다. 사용자는 설정 메뉴에서
   그 폴더를 열어 파일만 보내 주면 된다.

   자동 백업(문서\나의 캘린더 백업)과는 폴더도 파일도 완전히 별개다.
   =========================================================================== */

const LOG_FILE = 'render-errors.log';
const LOG_MAX_BYTES = 256 * 1024; // 이 크기를 넘으면 앞부분을 버린다 (무한정 자라지 않게)

function logFilePath() {
  return path.join(app.getPath('userData'), LOG_FILE);
}

function logLine(message) {
  try {
    const file = logFilePath();
    fs.mkdirSync(path.dirname(file), { recursive: true });
    try {
      // 앞부분을 잘라 최근 기록만 남긴다. 실패해도 append는 계속 시도한다.
      if (fs.statSync(file).size > LOG_MAX_BYTES) {
        const kept = fs.readFileSync(file, 'utf8').slice(-Math.floor(LOG_MAX_BYTES / 2));
        fs.writeFileSync(file, `[앞부분 생략]\n${kept}`, 'utf8');
      }
    } catch {
      /* 파일이 아직 없으면 statSync가 던진다 — 그냥 새로 쓴다 */
    }
    fs.appendFileSync(file, `${new Date().toISOString()} ${message}\n`, 'utf8');
  } catch {
    /* 로그를 남기려다 앱이 죽으면 본말전도다 */
  }
}

/*
   하드웨어 가속 끄기 스위치.

   오래된 그래픽 드라이버, 원격 데스크톱, 가상머신에서는 GPU 가속이 켜진 채로 뜨면
   화면이 하얗거나 까맣게 나오는 일이 드물지 않다. 그렇다고 모든 컴퓨터에서 끄면
   멀쩡한 기기의 렌더링 성능만 깎인다. 그래서 기본은 켜 두고,
   userData 폴더에 'disable-gpu' 파일을 만들어 둔 컴퓨터에서만 끈다
   (오류 로그 폴더와 같은 폴더라, 안내할 위치가 하나로 끝난다).
*/
function gpuDisabledByUser() {
  try {
    return (
      process.env.MYCAL_DISABLE_GPU === '1' ||
      fs.existsSync(path.join(app.getPath('userData'), 'disable-gpu')) ||
      fs.existsSync(path.join(app.getPath('userData'), 'disable-gpu.txt'))
    );
  } catch {
    return false;
  }
}

const gpuDisabled = gpuDisabledByUser();
if (gpuDisabled) app.disableHardwareAcceleration();

// 중복 실행 방지 — 이미 떠 있으면 기존 창에 포커스
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) app.quit();

let win = null;

function createWindow() {
  win = new BrowserWindow({
    width: 1320,
    height: 940,
    minWidth: 800,
    minHeight: 600,
    // 창이 뜨는 첫 프레임에 칠할 색. 렌더러가 localStorage의 테마 설정을 읽기 전이라
    // 메인 프로세스는 OS 설정(nativeTheme)밖에 알 수 없다. 그래도 이걸 봐 두면
    // OS가 다크일 때 흰 배경이 번쩍이는 건 막을 수 있다.
    // (사용자가 OS와 반대되는 테마를 골라 둔 경우엔 아주 잠깐 어긋날 수 있다.)
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#14131F' : '#F5F6FE',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, 'preload.cjs'),
    },
  });

  /*
     일반 실행 경로의 실패 감시. 스모크 테스트와 무관하게 항상 붙인다 —
     정작 필요한 건 개발자 컴퓨터가 아니라 사용자 컴퓨터에서다.
     화면이 비는 세 갈래를 구분할 수 있게 각각 다른 줄을 남긴다:
     로드 실패 / 렌더러 프로세스 사망 / preload 실패.
  */
  win.webContents.on('did-fail-load', (_e, code, desc, url, isMainFrame) => {
    logLine(`did-fail-load code=${code} desc=${desc} url=${url} mainFrame=${isMainFrame}`);
  });
  win.webContents.on('render-process-gone', (_e, details) => {
    // Electron 22+에서 'crashed'를 대체한 이벤트다
    logLine(`render-process-gone reason=${details.reason} exitCode=${details.exitCode}`);
  });
  win.webContents.on('preload-error', (_e, preloadPath, error) => {
    logLine(`preload-error path=${preloadPath} message=${error && error.message}`);
  });
  win.on('unresponsive', () => logLine('window unresponsive'));

  // 외부 링크는 기본 브라우저로 열기
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // 패키징 스모크 테스트용: MYCAL_SMOKE=<png경로> 로 실행하면 화면 캡처 후 종료
  const smokeTarget = process.env.MYCAL_SMOKE;
  if (smokeTarget) {
    const log = (msg) => {
      try {
        fs.appendFileSync(smokeTarget + '.log', `${new Date().toISOString()} ${msg}\n`);
      } catch {}
    };
    log('smoke start');
    win.webContents.on('did-fail-load', (_e, code, desc, url) => {
      log(`did-fail-load code=${code} desc=${desc} url=${url}`);
      app.quit();
    });
    win.webContents.once('did-finish-load', () => {
      log('did-finish-load');
      setTimeout(async () => {
        try {
          const image = await win.webContents.capturePage();
          fs.writeFileSync(smokeTarget, image.toPNG());
          log(`captured ${image.getSize().width}x${image.getSize().height}`);
        } catch (err) {
          log(`capture error: ${err.message}`);
        } finally {
          app.quit();
        }
      }, 2500);
    });
  }

  win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
}


/* ===========================================================================
   로컬 자동 백업

   렌더러는 샌드박스라 파일을 못 쓴다. 그래서 데이터는 렌더러가 넘기고,
   실제 파일 쓰기는 전부 여기서 한다.

   파일은 하루에 하나(my-calendar-backup-YYYY-MM-DD.json)만 만든다.
   앱을 켤 때 그날 파일이 없으면 만들고, 종료할 때 같은 파일을 최신 내용으로 덮어쓴다.
   하루에 여러 번 켰다 꺼도 파일이 불어나지 않고, 그날의 마지막 상태가 남는다.
   =========================================================================== */

const BACKUP_DIR_NAME = '나의 캘린더 백업';
const MAX_BACKUPS = 30;
const BACKUP_FILE_RE = /^my-calendar-backup-\d{4}-\d{2}-\d{2}\.json$/;

// 렌더러가 맡겨 둔 최신 데이터. 종료 시점에 이걸로 백업을 쓴다(디스크에는 그때 처음 닿는다).
let cachedSnapshot = null;

function backupDir() {
  return path.join(app.getPath('documents'), BACKUP_DIR_NAME);
}

/** 로컬 기준 오늘 날짜 'YYYY-MM-DD' (toISOString은 UTC라 날짜가 밀릴 수 있어 직접 만든다) */
function todayStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function listBackups(dir) {
  try {
    return fs.readdirSync(dir).filter((f) => BACKUP_FILE_RE.test(f)).sort();
  } catch {
    return [];
  }
}

/** 파일명에 ISO 날짜가 들어 있어 이름순 정렬 = 오래된 순. 앞에서부터 지운다. */
function pruneBackups(dir) {
  const files = listBackups(dir);
  for (const name of files.slice(0, Math.max(0, files.length - MAX_BACKUPS))) {
    try {
      fs.unlinkSync(path.join(dir, name));
    } catch {
      /* 지우기 실패는 무시 — 백업 자체는 이미 남았다 */
    }
  }
}

function writeBackup(json) {
  if (typeof json !== 'string' || json.length === 0) return { ok: false, reason: 'empty' };
  const dir = backupDir();
  try {
    fs.mkdirSync(dir, { recursive: true });
    const file = path.join(dir, `my-calendar-backup-${todayStamp()}.json`);
    fs.writeFileSync(file, json, 'utf8');
    pruneBackups(dir);
    return { ok: true, file, dir };
  } catch (err) {
    return { ok: false, reason: err.message };
  }
}

function backupStatus() {
  const dir = backupDir();
  const files = listBackups(dir);
  const newest = files[files.length - 1];
  let lastBackupAt = null;
  if (newest) {
    try {
      lastBackupAt = fs.statSync(path.join(dir, newest)).mtimeMs;
    } catch {
      /* 무시 */
    }
  }
  return {
    dir,
    count: files.length,
    lastBackupAt,
    todayDone: files.includes(`my-calendar-backup-${todayStamp()}.json`),
  };
}

/* ===========================================================================
   할 일 알림

   앱을 켤 때 남아 있는 할 일이 있으면 한 번 알려 준다. 하루에 여러 번 켜도
   그날 이미 띄웠으면 건너뛴다 — 자동 백업이 '하루에 파일 하나'로 관리하는 것과 같은 결로,
   마지막으로 띄운 날짜를 userData에 적어 두고 비교한다.

   문구는 여기서 만든다. 하루 한 번 판정이 이쪽에 있어 렌더러가 만든 문장은 대부분
   버려지고, 알림 제목/본문 형식은 OS에 보여줄 표현이라 메인이 갖는 편이 자연스럽다.
   =========================================================================== */

const NOTICE_STAMP_FILE = 'last-todo-notice';

function noticeStampPath() {
  return path.join(app.getPath('userData'), NOTICE_STAMP_FILE);
}

function noticeAlreadyShownToday() {
  try {
    return fs.readFileSync(noticeStampPath(), 'utf8').trim() === todayStamp();
  } catch {
    return false; // 파일이 없으면 아직 안 띄운 것
  }
}

function markNoticeShown() {
  try {
    fs.mkdirSync(app.getPath('userData'), { recursive: true });
    fs.writeFileSync(noticeStampPath(), todayStamp(), 'utf8');
  } catch {
    /* 기록에 실패하면 다음 실행에 한 번 더 뜰 뿐이다 */
  }
}

/** '할 일이 3개 있어요' / 밀린 게 섞여 있으면 그 사실만 덧붙인다 (재촉하지 않는다) */
function noticeBody(today, overdue) {
  const total = today + overdue;
  if (overdue > 0) return `할 일이 ${total}개 있어요 (밀린 것 ${overdue}개 포함)`;
  return `오늘 할 일이 ${total}개 있어요`;
}

ipcMain.handle('notify:todos', (_event, counts) => {
  const today = Number(counts && counts.today) || 0;
  const overdue = Number(counts && counts.overdue) || 0;
  if (today + overdue <= 0) return { shown: false, reason: 'empty' };
  if (!Notification.isSupported()) return { shown: false, reason: 'unsupported' };
  if (noticeAlreadyShownToday()) return { shown: false, reason: 'already-today' };
  try {
    const notification = new Notification({
      title: '나의 캘린더',
      body: noticeBody(today, overdue),
      silent: false,
    });
    // 알림을 누르면 이미 떠 있는 창을 앞으로 (second-instance와 같은 동작)
    notification.on('click', () => {
      if (!win) return;
      if (win.isMinimized()) win.restore();
      win.focus();
    });
    notification.show();
    markNoticeShown();
    return { shown: true, body: noticeBody(today, overdue) };
  } catch (err) {
    logLine(`notify failed: ${err.message}`);
    return { shown: false, reason: 'error' };
  }
});

ipcMain.on('diag:report', (_event, message) => {
  if (typeof message === 'string') logLine(message.slice(0, 4000));
});

ipcMain.handle('diag:open-folder', async () => {
  const file = logFilePath();
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    // 아직 아무 사고도 없었다면 파일이 없다. 빈손으로 폴더만 열면 뭘 찾아야 할지 모르니
    // 안내 한 줄이 담긴 파일을 만들어 두고 그 파일을 선택된 상태로 보여 준다.
    if (!fs.existsSync(file)) {
      fs.writeFileSync(file, '아직 기록된 오류가 없어요.\n', 'utf8');
    }
    shell.showItemInFolder(file);
    return file;
  } catch (err) {
    return `open-failed: ${err.message}`;
  }
});

ipcMain.handle('backup:run', (_event, json) => writeBackup(json));
ipcMain.handle('backup:status', () => backupStatus());
ipcMain.handle('backup:open-folder', async () => {
  const dir = backupDir();
  try {
    fs.mkdirSync(dir, { recursive: true });
  } catch {
    /* 무시 */
  }
  return shell.openPath(dir);
});
ipcMain.on('backup:cache', (_event, json) => {
  if (typeof json === 'string') cachedSnapshot = json;
});

// 종료 직전에 그날 파일을 최신 내용으로 덮어쓴다. 동기 쓰기라 종료를 붙잡지 않아도 된다.
app.on('before-quit', () => {
  if (cachedSnapshot) writeBackup(cachedSnapshot);
});

Menu.setApplicationMenu(null);

app.whenReady().then(() => {
  logLine(
    `app start version=${app.getVersion()} electron=${process.versions.electron} ` +
      `os=${process.platform}/${process.getSystemVersion?.() ?? '?'} gpuDisabled=${gpuDisabled}`,
  );
  createWindow();
});

// GPU 프로세스가 죽는 것도 빈 화면의 흔한 원인이다 (이때 disable-gpu 스위치가 답이 된다)
app.on('child-process-gone', (_event, details) => {
  logLine(`child-process-gone type=${details.type} reason=${details.reason}`);
});

app.on('second-instance', () => {
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.on('window-all-closed', () => app.quit());
