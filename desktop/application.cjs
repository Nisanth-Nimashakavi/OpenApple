'use strict';
const {
  app,
  BrowserWindow,
  Tray,
  Menu,
  ipcMain,
  nativeImage,
  screen,
  dialog,
} = require('electron');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const fs = require('node:fs');
const os = require('node:os');
const { pathToFileURL } = require('node:url');
const { Backend } = require('./backend.cjs');
const { credentials, startBridge } = require('./bridge.cjs');
const { Reviews } = require('./reviews.cjs');
const { pythonBinary } = require('./runtime.cjs');
const { ChatDelivery } = require('./delivery.cjs');
const chatDelivery = new ChatDelivery();
const { FeedCoordinator } = require('./feeding.cjs');
let feeder;
const manualTargets = new Map();

let window, tray, backend, server, reviews, expiryTimer;
let stopping = false;
let startupComplete = false;
const directory = process.env.OPENAPPLE_DATA_DIR || path.join(os.homedir(), '.openapple');
const port = Number(process.env.OPENAPPLE_PORT || 52199);
const rendererURL = pathToFileURL(path.join(root, 'overlay.html')).href;

function trusted(event) {
  return (
    window &&
    event.sender === window.webContents &&
    event.senderFrame === window.webContents.mainFrame &&
    event.senderFrame.url === rendererURL
  );
}

function reveal() {
  window.setIgnoreMouseEvents(false);
  window.setFocusable(true);
  window.setBounds(screen.getDisplayNearestPoint(screen.getCursorScreenPoint()).bounds);
  window.show();
  window.focus();
}

async function showRequest(request, count) {
  if (request.source !== 'mcp') {
    const target =
      manualTargets.get(request.id) ||
      (await chatDelivery.automatic(request.agent).catch(() => null));
    if (target) {
      request = await backend.call('assign', {
        request_id: request.id,
        agent: target.agent,
        recipient: target.label.slice(0, 1000),
      });
      manualTargets.set(request.id, target);
      reviews.current = request;
    }
  }
  reveal();
  await chatDelivery
    .positionOverlay(process.pid, 'OpenApple feeder', window.getBounds())
    .catch((error) => console.error(error.message));
  await menu();
  window.webContents.send('review', {
    ...request,
    queueCount: count,
    delivery: request.source === 'mcp' ? 'mcp' : 'chat',
    cursor: screen.getCursorScreenPoint(),
    bounds: window.getBounds(),
    muted: ['0', 'false', 'no'].includes((process.env.OPENAPPLE_SOUND || '1').toLowerCase()),
  });
}

async function manualReview() {
  if (window.isVisible()) {
    window.webContents.send('drop-apple');
    return;
  }
  const waiting = await backend.call('pending');
  if (reviews.current) {
    if (window.isVisible()) window.webContents.send('drop-apple');
    else reveal();
    return;
  }
  if (waiting.length) {
    await reviews.refresh();
    return;
  }
  const target = await chatDelivery.automatic().catch(() => null);
  const request = await backend.call('create', {
    task: 'Good job on the task!',
    agent: target?.agent || 'Agent',
    variety: 'Honeycrisp',
    source: 'desktop',
    recipient: target?.label.slice(0, 1000) || '',
  });
  if (target) manualTargets.set(request.id, target);
  await reviews.refresh();
}

async function menu() {
  if (!tray) return;
  const state = await backend.call('snapshot');
  tray.setToolTip(
    `OpenApple - ${state.total_apples} apple${state.total_apples === 1 ? '' : 's'} fed! Click to feed Claude/AGY/Codex`,
  );
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: '🍎 Feed Apple Now', click: () => manualReview().catch(report) },
      { label: `Total Fed: ${state.total_apples} 🍏`, enabled: false },
      { type: 'separator' },
      { label: 'Quit OpenApple', click: () => app.quit() },
    ]),
  );
}

function report(error) {
  console.error(error.message);
  if (app.isReady()) dialog.showErrorBox('OpenApple needs attention', error.message);
}

async function init() {
  if (!Number.isInteger(port) || port < 1024 || port > 65535)
    throw new Error('Invalid OPENAPPLE_PORT');
  fs.mkdirSync(path.join(directory, 'desktop'), { recursive: true, mode: 0o700 });
  app.setPath('userData', path.join(directory, 'desktop'));
  // Chromium's instance lock is acquired before creating any desktop resources.
  if (!app.requestSingleInstanceLock()) {
    app.quit();
    return;
  }
  app.on('second-instance', (_event, argv) => {
    if (!argv.includes('--tray-only') && !argv.includes('--daemon')) manualReview().catch(report);
  });
  await app.whenReady();
  const token = credentials(directory);
  backend = new Backend(pythonBinary(), {
    cwd: root,
    env: { ...process.env, OPENAPPLE_DESKTOP_DIR: root },
  });
  backend.on('fatal', (error) => {
    // Initialization failures already propagate through the awaited health call.
    if (!stopping && startupComplete) {
      report(error);
      app.quit();
    }
  });
  await backend.call('health');
  window = new BrowserWindow({
    ...screen.getPrimaryDisplay().bounds,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    show: false,
    hasShadow: false,
    title: 'OpenApple feeder',
    webPreferences: {
      preload: path.join(root, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  if (process.platform === 'darwin') window.setAlwaysOnTop(true, 'screen-saver');
  const place = () =>
    window.setBounds(screen.getDisplayNearestPoint(screen.getCursorScreenPoint()).bounds);
  screen.on('display-removed', place);
  screen.on('display-metrics-changed', place);
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event) => event.preventDefault());
  window.on('close', (event) => {
    if (!stopping) {
      event.preventDefault();
      window.hide();
      if (reviews.current)
        reviews
          .decide(reviews.current.id, 'cancelled', '')
          .then(() => reviews.advance())
          .catch(report);
    }
  });
  await window.loadFile(path.join(root, 'overlay.html'));
  reviews = new Reviews(backend, showRequest, () => {
    window.webContents.send('dismiss');
    window.hide();
  });
  feeder = new FeedCoordinator({
    backend,
    reviews,
    delivery: chatDelivery,
    targets: manualTargets,
    window,
    showRequest,
    onCommitted: () => window.webContents.send('fed'),
  });
  ipcMain.handle('decision', async (event, message) => {
    if (!trusted(event)) throw new Error('Untrusted review sender');
    if (
      !message ||
      typeof message !== 'object' ||
      Object.keys(message).some((k) => !['id', 'outcome', 'note'].includes(k))
    )
      throw new Error('Invalid decision');
    if (!['approved', 'rejected', 'cancelled'].includes(message.outcome))
      throw new Error('Invalid outcome');
    const result = await feeder.decide(message);
    if (result.deliveryError) console.error('Apple delivery failed:', result.deliveryError);
    await menu().catch((error) => console.error(error.message));
    // Let the renderer display the committed result before advancing the queue.
    setTimeout(
      () => {
        if (!stopping) {
          window.webContents.send('dismiss');
          window.hide();
          window.setIgnoreMouseEvents(false);
          window.setFocusable(true);
          reviews.advance().catch(report);
        }
      },
      result.delivery_status === 'failed' ? 5000 : 1700,
    );
    return result;
  });
  ipcMain.on('hide-overlay', (event) => {
    if (trusted(event) && !reviews.current) window.hide();
  });
  ipcMain.on('renderer-error', (event, message) => {
    if (trusted(event)) report(new Error(String(message).slice(0, 1000)));
  });
  server = await startBridge({ backend, token, port, changed: () => reviews.refresh() });
  const icon = nativeImage.createFromPath(
    path.join(root, 'icon', process.platform === 'win32' ? 'icon.ico' : 'Template.png'),
  );
  if (process.platform === 'darwin') icon.setTemplateImage(true);
  if (!icon.isEmpty()) {
    tray = new Tray(icon.resize({ width: 22, height: 22 }));
    tray.on('click', () => {
      manualReview().catch(report);
    });
    await menu();
  }
  expiryTimer = setInterval(() => reviews.refresh().catch(report), 1000);
  await reviews.refresh();
  startupComplete = true;
  if (
    !process.argv.includes('--tray-only') &&
    !process.argv.includes('--daemon') &&
    !reviews.current
  )
    await manualReview();
}
app.on('before-quit', () => {
  stopping = true;
  clearInterval(expiryTimer);
  server?.close();
  backend?.close();
});
app.on('window-all-closed', () => {});
init().catch((error) => {
  report(error);
  app.quit();
});
