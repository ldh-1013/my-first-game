const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('path');
const fs = require('fs');

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
    backgroundColor: '#F5F6FE',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

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

Menu.setApplicationMenu(null);

app.whenReady().then(createWindow);

app.on('second-instance', () => {
  if (win) {
    if (win.isMinimized()) win.restore();
    win.focus();
  }
});

app.on('window-all-closed', () => app.quit());
