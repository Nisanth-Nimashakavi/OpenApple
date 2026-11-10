const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const http = require('http');
const { execFile, execFileSync } = require('child_process');

// ── Win32 FFI (Windows optional acceleration) ────────────────────────────────
let keybd_event;
if (process.platform === 'win32') {
  try {
    const koffi = require('koffi');
    const user32 = koffi.load('user32.dll');
    keybd_event = user32.func('void __stdcall keybd_event(uint8_t bVk, uint8_t bScan, uint32_t dwFlags, uintptr_t dwExtraInfo)');
  } catch (e) {
    // Falls back to PowerShell base64 Unicode injection below
  }
}

// ── Ledger Storage ──────────────────────────────────────────────────────────
const LEDGER_PATH = path.join(os.homedir(), '.openapple', 'ledger.json');

function getLedger() {
  try {
    if (fs.existsSync(LEDGER_PATH)) {
      return JSON.parse(fs.readFileSync(LEDGER_PATH, 'utf8'));
    }
  } catch (e) {}
  return { total_apples: 0, current_streak: 0, history: [] };
}

function recordFeed(task = 'Good job!', variety = 'Honeycrisp', agent = 'claude') {
  const ledger = getLedger();
  ledger.total_apples = (ledger.total_apples || 0) + 1;
  ledger.current_streak = (ledger.current_streak || 0) + 1;
  if (!ledger.history) ledger.history = [];
  ledger.history.push({
    task,
    variety,
    agent,
    approved: true,
    note: `Fed to ${agent} via OpenApple overlay`,
    timestamp: new Date().toISOString(),
  });
  try {
    fs.mkdirSync(path.dirname(LEDGER_PATH), { recursive: true });
    fs.writeFileSync(LEDGER_PATH, JSON.stringify(ledger, null, 2));
  } catch (e) {
    console.warn('Failed to write ledger:', e.message);
  }
  return ledger.total_apples;
}

// ── Globals ─────────────────────────────────────────────────────────────────
let tray = null;
let overlay = null;
let overlayReady = false;
let spawnQueued = false;
let pendingFeedDetails = null;
let lastActiveTarget = null;

const isHyprland = !!process.env.HYPRLAND_INSTANCE_SIGNATURE;
const isWayland = !!process.env.WAYLAND_DISPLAY;

// Blacklist browsers & chat apps so we NEVER type into search bars, chat windows, etc.
const BROWSER_CLASSES = new Set([
  'firefox', 'zen', 'brave-browser', 'chromium', 'google-chrome',
  'floorp', 'librewolf', 'vivaldi', 'microsoft-edge', 'tor-browser',
  'discord', 'slack', 'telegram-desktop', 'spotify', 'chrome.exe',
  'firefox.exe', 'msedge.exe', 'brave.exe', 'opera.exe'
]);

// ── Strict Agent Detection (Claude, AGY, Codex Only) ────────────────────────
function findAgentTarget(requestedAgent = null) {
  if (requestedAgent) {
    const norm = requestedAgent.toLowerCase();
    if (['claude', 'agy', 'codex'].includes(norm)) {
      requestedAgent = norm;
    }
  }

  // 1. Linux / Hyprland (Wayland)
  if (isHyprland) {
    try {
      const clientsJson = JSON.parse(execFileSync('hyprctl', ['clients', '-j'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }));
      const psOut = execFileSync('ps', ['-eo', 'pid,ppid,comm,args'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
      const lines = psOut.split('\n');
      const children = {};

      for (const l of lines) {
        const parts = l.trim().split(/\s+/);
        if (parts.length >= 3) {
          const p = parseInt(parts[0], 10);
          const pp = parseInt(parts[1], 10);
          const comm = parts[2];
          const args = parts.slice(3).join(' ');
          if (!children[pp]) children[pp] = [];
          children[pp].push({ pid: p, comm, args });
        }
      }

      function getTerminalAgent(pid) {
        if (!pid) return null;
        function check(p) {
          const kids = children[p] || [];
          for (const k of kids) {
            const commLower = k.comm.toLowerCase();
            const argsLower = (k.args || '').toLowerCase();

            // Ignore browser extensions and background bridge helpers
            if (argsLower.includes('native-messaging') || argsLower.includes('claudecodebrowser')) continue;

            if (commLower === 'claude' || /\bclaude(\.js|\.exe)?\b/.test(argsLower)) return 'claude';
            if (commLower === 'agy' || /\bagy(\.js|\.exe)?\b/.test(argsLower)) return 'agy';
            if (commLower === 'codex' || /\bcodex(\.js|\.exe)?\b/.test(argsLower)) return 'codex';

            const sub = check(k.pid);
            if (sub) return sub;
          }
          return null;
        }
        return check(pid);
      }

      const sorted = [...clientsJson].sort((a, b) => (a.focusHistoryID ?? 99) - (b.focusHistoryID ?? 99));

      for (const c of sorted) {
        const clazz = (c.class || '').toLowerCase();
        if (BROWSER_CLASSES.has(clazz)) continue;
        if (c.title === 'openapple-overlay' || clazz === 'openapple') continue;

        if (clazz === 'claude-desktop' || clazz === 'claude') {
          if (!requestedAgent || requestedAgent === 'claude') {
            return { address: c.address, agent: 'claude', title: c.title, platform: 'hyprland' };
          }
        }

        const agent = getTerminalAgent(c.pid);
        if (agent) {
          if (!requestedAgent || requestedAgent === agent) {
            return { address: c.address, agent, title: c.title, platform: 'hyprland' };
          }
        }
      }
    } catch (e) {
      console.warn('Hyprland agent detection error:', e.message);
    }
    return null;
  }

  // 2. macOS (Darwin)
  if (process.platform === 'darwin') {
    try {
      const psOut = execFileSync('ps', ['-eo', 'comm,args'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).toLowerCase();
      const hasClaude = /\bclaude(\.js)?\b/.test(psOut);
      const hasAgy = /\bagy(\.js)?\b/.test(psOut);
      const hasCodex = /\bcodex(\.js)?\b/.test(psOut);

      const detectedAgent = requestedAgent || (hasClaude ? 'claude' : hasAgy ? 'agy' : hasCodex ? 'codex' : null);

      if (detectedAgent) {
        // Query the frontmost non-OpenApple application
        const script = [
          'tell application "System Events"',
          '  set procList to name of every application process whose visible is true and name is not "Electron" and name is not "openapple"',
          '  if (count of procList) > 0 then',
          '    return item 1 of procList',
          '  else',
          '    return ""',
          '  end if',
          'end tell',
        ].join('\n');
        let frontApp = '';
        try {
          frontApp = execFileSync('osascript', ['-e', script], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
        } catch (e) {}

        const TERMINALS = ['Terminal', 'iTerm2', 'iTerm', 'kitty', 'Alacritty', 'Ghostty', 'WezTerm', 'Claude', 'Code', 'Cursor'];
        const matchedApp = TERMINALS.find(t => t.toLowerCase() === frontApp.toLowerCase());
        // STRICT SAFETY: If frontmost app is a browser or unapproved app, NEVER type!
        if (!matchedApp) return null;

        return { appName: matchedApp, agent: detectedAgent, title: frontApp, platform: 'darwin' };
      }
    } catch (e) {}
    return null;
  }

  // 3. Windows (win32)
  if (process.platform === 'win32') {
    try {
      const tasklist = execFileSync('tasklist', ['/FO', 'CSV'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).toLowerCase();
      const hasClaude = tasklist.includes('claude');
      const hasAgy = tasklist.includes('agy');
      const hasCodex = tasklist.includes('codex');

      const detectedAgent = requestedAgent || (hasClaude ? 'claude' : hasAgy ? 'agy' : hasCodex ? 'codex' : null);

      if (detectedAgent) {
        // Query the active foreground window process
        const psActive = `
          Add-Type @"
          using System;
          using System.Runtime.InteropServices;
          public class W32 {
            [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
            [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
          }
"@
          $h = [W32]::GetForegroundWindow()
          $p = 0
          [W32]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
          (Get-Process -Id $p -ErrorAction SilentlyContinue).ProcessName
        `.replace(/\r?\n\s*/g, ' ');
        let frontProc = '';
        try {
          frontProc = execFileSync('powershell', ['-NoProfile', '-NonInteractive', '-Command', psActive], { encoding: 'utf8', timeout: 500 }).trim().toLowerCase();
        } catch (e) {}

        if (frontProc && BROWSER_CLASSES.has(frontProc + '.exe')) {
          return null;
        }

        const WIN_TERMINALS = ['windowsterminal', 'powershell', 'pwsh', 'cmd', 'code', 'cursor', 'claude', 'mintty', 'conhost'];
        const matched = WIN_TERMINALS.find(t => t === frontProc);
        if (!matched && frontProc && frontProc !== 'electron') {
          return null;
        }

        let appTitle = 'Windows Terminal';
        if (frontProc === 'code') appTitle = 'Visual Studio Code';
        else if (frontProc === 'cursor') appTitle = 'Cursor';
        else if (frontProc === 'powershell' || frontProc === 'pwsh') appTitle = 'PowerShell';
        else if (frontProc === 'cmd') appTitle = 'Command Prompt';
        else if (frontProc === 'claude') appTitle = 'Claude';

        return { agent: detectedAgent, title: appTitle, platform: 'win32' };
      }
    } catch (e) {}
    return null;
  }

  // 4. Linux / Generic X11 & Wayland
  if (process.platform === 'linux' && !isHyprland) {
    try {
      const psOut = execFileSync('ps', ['-eo', 'comm,args'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).toLowerCase();
      const hasClaude = /\bclaude(\.js)?\b/.test(psOut);
      const hasAgy = /\bagy(\.js)?\b/.test(psOut);
      const hasCodex = /\bcodex(\.js)?\b/.test(psOut);
      const detected = requestedAgent || (hasClaude ? 'claude' : hasAgy ? 'agy' : hasCodex ? 'codex' : null);

      if (detected) {
        // On X11, verify active window isn't a browser and is a terminal
        let activeWin = null;
        try {
          const winId = execFileSync('xdotool', ['getactivewindow'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
          const winClass = execFileSync('xdotool', ['getwindowclassname', winId], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim().toLowerCase();
          if (BROWSER_CLASSES.has(winClass)) return null;

          const TERMINAL_CLASSES = new Set([
            'kitty', 'alacritty', 'ghostty', 'wezterm', 'foot', 'xterm',
            'gnome-terminal', 'konsole', 'tilix', 'terminator', 'urxvt',
            'code', 'cursor', 'claude-desktop', 'claude'
          ]);
          if (winClass && !TERMINAL_CLASSES.has(winClass)) return null;
          activeWin = winId;
        } catch (e) {}

        return { windowId: activeWin, agent: detected, title: 'Terminal', platform: isWayland ? 'wayland' : 'x11' };
      }
    } catch (e) {}
    return null;
  }

  return null;
}

// ── Hyprland Window Rules Setup ─────────────────────────────────────────────
function applyHyprlandRules() {
  if (!isHyprland) return;
  try {
    execFile('hyprctl', ['keyword', 'windowrule', 'float, match:title ^(openapple-overlay)$']);
    execFile('hyprctl', ['keyword', 'windowrule', 'pin, match:title ^(openapple-overlay)$']);
    execFile('hyprctl', ['keyword', 'windowrule', 'move 0 0, match:title ^(openapple-overlay)$']);
    execFile('hyprctl', ['keyword', 'windowrule', 'size 100% 100%, match:title ^(openapple-overlay)$']);
    execFile('hyprctl', ['keyword', 'windowrule', 'noborder, match:title ^(openapple-overlay)$']);
    execFile('hyprctl', ['keyword', 'windowrule', 'noshadow, match:title ^(openapple-overlay)$']);
    execFile('hyprctl', ['keyword', 'windowrule', 'noanim, match:title ^(openapple-overlay)$']);
  } catch (e) {}
}

// ── Tray Icon (Cross-Platform) ──────────────────────────────────────────────
function getTrayIcon() {
  const iconDir = path.join(__dirname, 'icon');

  if (process.platform === 'win32') {
    const icoPath = path.join(iconDir, 'icon.ico');
    if (fs.existsSync(icoPath)) {
      const img = nativeImage.createFromPath(icoPath);
      if (!img.isEmpty()) return img;
    }
  }

  const tmplPath = path.join(iconDir, 'Template.png');
  if (fs.existsSync(tmplPath)) {
    const img = nativeImage.createFromPath(tmplPath);
    if (!img.isEmpty()) {
      if (process.platform === 'darwin') img.setTemplateImage(true);
      return img.resize({ width: 22, height: 22 });
    }
  }

  const pngPath = path.join(iconDir, 'icon.png');
  if (fs.existsSync(pngPath)) {
    const img = nativeImage.createFromPath(pngPath);
    if (!img.isEmpty()) return img.resize({ width: 22, height: 22 });
  }

  return nativeImage.createEmpty();
}

function updateTrayMenu() {
  if (!tray) return;
  const count = getLedger().total_apples || 0;
  tray.setToolTip(`OpenApple - ${count} apple${count === 1 ? '' : 's'} fed! Click to feed Claude/AGY/Codex`);
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: '🍎 Feed Apple Now', click: () => toggleOverlay() },
      { label: `Total Fed: ${count} 🍏`, enabled: false },
      { type: 'separator' },
      { label: 'Quit OpenApple', click: () => app.quit() },
    ])
  );
}

// ── Overlay Window ──────────────────────────────────────────────────────────
function createOverlay() {
  applyHyprlandRules();

  const { bounds } = screen.getPrimaryDisplay();

  overlay = new BrowserWindow({
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    focusable: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    show: false,
    title: 'openapple-overlay',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  if (process.platform === 'darwin') {
    overlay.setAlwaysOnTop(true, 'screen-saver');
  } else {
    overlay.setAlwaysOnTop(true);
  }
  overlayReady = false;

  overlay.loadFile('overlay.html');

  overlay.webContents.on('did-finish-load', () => {
    overlayReady = true;
    if (spawnQueued) {
      spawnQueued = false;
      showOverlay(pendingFeedDetails || {});
    }
  });

  overlay.on('closed', () => {
    overlay = null;
    overlayReady = false;
    spawnQueued = false;
  });
}

function showOverlay(details = {}) {
  // Capture active agent BEFORE overlay takes window focus
  lastActiveTarget = findAgentTarget(details.agent);

  if (!overlay) createOverlay();

  // Position overlay on current active display (macOS & Windows)
  if (process.platform === 'darwin' || process.platform === 'win32') {
    try {
      const cursorPoint = screen.getCursorScreenPoint();
      const display = screen.getDisplayNearestPoint(cursorPoint);
      if (display && display.bounds) {
        overlay.setBounds(display.bounds);
      }
    } catch (e) {}
  }

  const agentTarget = lastActiveTarget;
  details.target = agentTarget;
  details.agent = agentTarget ? agentTarget.agent : 'universal';
  details.agentTitle = agentTarget ? agentTarget.title : 'Claude/AGY/Codex';
  details.targetAddress = agentTarget ? agentTarget.address : null;

  overlay.show();
  overlay.focus();

  if (isHyprland) {
    try {
      execFile('hyprctl', ['dispatch', 'pin', 'active']);
    } catch (e) {}
  }

  overlay.webContents.send('spawn-apple', details);
}

function hideOverlay() {
  if (overlay && overlay.isVisible()) {
    overlay.hide();
  }
}

function toggleOverlay(details = null) {
  pendingFeedDetails = details;

  if (overlay && overlay.isVisible()) {
    overlay.webContents.send('drop-apple');
    return;
  }

  if (!overlayReady) {
    spawnQueued = true;
    if (!overlay) createOverlay();
  } else {
    showOverlay(details || {});
  }
}

// ── Cross-Platform Macro Sending ────────────────────────────────────────────
function sendMacroWindows(text, targetTitle) {
  // 1. Activate target window if known
  if (targetTitle) {
    const actScript = `(New-Object -ComObject WScript.Shell).AppActivate('${targetTitle}')`;
    try {
      execFileSync('powershell', ['-NoProfile', '-NonInteractive', '-Command', actScript], { timeout: 400 });
    } catch (e) {}
  }

  // 2. Direct Win32 Unicode keystrokes via koffi FFI if available
  if (keybd_event) {
    const KEYEVENTF_KEYUP = 0x0002;
    const KEYEVENTF_UNICODE = 0x0004;
    for (let i = 0; i < text.length; i++) {
      const code = text.charCodeAt(i);
      keybd_event(0, code, KEYEVENTF_UNICODE, 0);
      keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0);
    }
    keybd_event(0x0D, 0, 0, 0); // Enter down
    keybd_event(0x0D, 0, KEYEVENTF_KEYUP, 0); // Enter up
    return;
  }

  // 3. Robust PowerShell UTF-16LE Base64 clipboard paste fallback (100% Unicode / Emoji support)
  const b64 = Buffer.from(text, 'utf16le').toString('base64');
  const psScript = `
    $raw = [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String('${b64}'));
    Set-Clipboard -Value $raw;
    Add-Type -AssemblyName System.Windows.Forms;
    [System.Windows.Forms.SendKeys]::SendWait('^v{ENTER}');
  `.replace(/\r?\n\s*/g, ' ');

  execFile('powershell', ['-NoProfile', '-NonInteractive', '-Command', psScript], () => {});
}

function sendRewardMacro(details = {}) {
  const variety = details.variety || 'Honeycrisp';
  const requestedAgent = details.agent || null;

  // STRICTLY find Claude, AGY, or Codex window (use target captured right before overlay took focus)
  const target = (details && details.target) || lastActiveTarget || findAgentTarget(requestedAgent);
  lastActiveTarget = null; // Clear so subsequent runs never use a stale target!

  // Re-verify that target window is still alive
  if (target && target.platform === 'hyprland' && target.address) {
    try {
      const clientsJson = JSON.parse(execFileSync('hyprctl', ['clients', '-j'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }));
      const exists = clientsJson.some(c => c.address === target.address);
      if (!exists) {
        console.log('[OpenApple] Target window closed. Aborting macro injection.');
        return;
      }
    } catch (e) {
      return;
    }
  }

  // SAFETY CHECK: If no Claude, AGY, or Codex window is found, DO NOT TYPE ANYTHING!
  if (!target) {
    console.log('[OpenApple] Safety: No active Claude, AGY, or Codex window found. Aborting keyboard injection.');
    return;
  }

  const agentName = target.agent.toUpperCase();
  const phrases = [
    `🍎 *CRUNCH* Good job ${agentName}! Take an apple! [${variety}]`,
    `🍎 Delicious ${variety}! Outstanding work ${agentName}! *nom nom nom*`,
    `🍎 +1 Apple for ${agentName}! Fantastic task execution, keep it up!`,
    `🍎 *CRUNCH* Well done ${agentName}! Sweet and crisp reward for you!`,
    `🍎 *chomp* So good ${agentName}! Excellent work!`,
    `🍎 Tasty apple reward for ${agentName}! 10/10!`,
  ];
  const chosen = phrases[Math.floor(Math.random() * phrases.length)];

  // Allow 380ms for user to experience the celebratory crunch animation & juice burst
  setTimeout(() => {
    hideOverlay();

    // Focus the specific agent window per platform
    if (target.platform === 'hyprland' && target.address) {
      try {
        execFileSync('hyprctl', ['dispatch', 'focuswindow', `address:${target.address}`]);
      } catch (e) {}
    } else if (target.platform === 'darwin' && target.appName) {
      try {
        execFile('osascript', ['-e', `tell application "${target.appName}" to activate`]);
      } catch (e) {}
    } else if (target.platform === 'x11' && target.windowId) {
      try {
        execFile('xdotool', ['windowactivate', '--sync', target.windowId], () => {});
      } catch (e) {}
    }

  setTimeout(() => {
    if (isHyprland || isWayland) {
      execFile('wtype', ['-d', '1', chosen], err => {
        if (!err) {
          setTimeout(() => {
            execFile('wtype', ['-k', 'Return'], () => {});
          }, 40);
        }
      });
    } else if (process.platform === 'darwin') {
      const escaped = chosen.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
      const script = `tell application "System Events"\n keystroke "${escaped}"\n key code 36\nend tell`;
      execFile('osascript', ['-e', script], () => {});
    } else if (process.platform === 'win32') {
      sendMacroWindows(chosen, target.title);
    } else if (process.platform === 'x11') {
      execFile('xdotool', ['type', '--delay', '1', '--clearmodifiers', '--', chosen, 'key', 'Return'], () => {});
    }
  }, 180);
}, 380);
}

// ── IPC Handlers ────────────────────────────────────────────────────────────
ipcMain.on('feed-apple', (event, details) => {
  const variety = (details && details.variety) || 'Honeycrisp';
  const task = (details && details.task) || 'Good job!';
  const agent = (details && details.agent) || 'claude';
  recordFeed(task, variety, agent);
  updateTrayMenu();
  try {
    sendRewardMacro(details || {});
  } catch (e) {
    console.warn('Macro error:', e.message);
  }
});

ipcMain.on('hide-overlay', () => {
  hideOverlay();
});

// ── Local HTTP Server (Bridge for MCP & CLI) ────────────────────────────────
function startLocalBridge() {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1:52199');
    res.setHeader('Content-Type', 'application/json');

    if (url.pathname === '/feed' || url.pathname === '/trigger') {
      const task = url.searchParams.get('task') || 'Milestone achieved!';
      const variety = url.searchParams.get('variety') || 'Honeycrisp';
      const agent = url.searchParams.get('agent') || '';
      toggleOverlay({ task, variety, agent });
      res.writeHead(200);
      res.end(JSON.stringify({ status: 'overlay_triggered', task, variety, agent }));
      return;
    }

    if (url.pathname === '/status') {
      const ledger = getLedger();
      res.writeHead(200);
      res.end(JSON.stringify(ledger));
      return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ error: 'not_found' }));
  });

  server.listen(52199, '127.0.0.1', () => {
    console.log('[OpenApple] Bridge listening on 127.0.0.1:52199');
  });
  server.on('error', err => {
    console.error('[OpenApple] Bridge server error:', err.message);
  });
}

// ── Robust Cross-Platform Single Instance Initialization ────────────────────
function cleanStaleLocks() {
  try {
    const sys = process.platform;
    let configDir;
    if (sys === 'darwin') {
      configDir = path.join(os.homedir(), 'Library', 'Application Support', 'openapple');
    } else if (sys === 'win32') {
      configDir = path.join(process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'), 'openapple');
    } else {
      configDir = path.join(os.homedir(), '.config', 'openapple');
    }
    for (const f of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
      const p = path.join(configDir, f);
      if (fs.existsSync(p)) fs.unlinkSync(p);
    }
  } catch (e) {}
}

async function init() {
  console.log('[OpenApple] Checking bridge...');
  const isRunning = await new Promise(resolve => {
    const req = http.get('http://127.0.0.1:52199/status', { timeout: 300 }, res => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });

  if (isRunning) {
    console.log('[OpenApple] Existing instance found, triggering feed and exiting.');
    http.get('http://127.0.0.1:52199/feed', () => app.quit()).on('error', () => app.quit());
    return;
  }

  cleanStaleLocks();

  console.log('[OpenApple] Requesting single instance lock...');
  const gotLock = app.requestSingleInstanceLock();
  console.log('[OpenApple] gotLock:', gotLock);
  if (!gotLock) {
    console.log('[OpenApple] Lock denied, quitting.');
    app.quit();
    return;
  }

  app.on('second-instance', () => {
    toggleOverlay();
  });

  console.log('[OpenApple] Waiting for app.whenReady()...');
  await app.whenReady();
  console.log('[OpenApple] App ready!');
  applyHyprlandRules();

  startLocalBridge();

  try {
    const icon = getTrayIcon();
    if (icon && !icon.isEmpty()) {
      tray = new Tray(icon);
      updateTrayMenu();
      tray.on('click', () => toggleOverlay());
      console.log('[OpenApple] Tray initialized.');
    }
  } catch (e) {
    console.warn('[OpenApple] Tray initialization error:', e.message);
  }

  try {
    createOverlay();
  } catch (e) {
    console.error('[OpenApple] createOverlay error:', e.message);
  }

  const args = process.argv.slice(2);
  if (!args.includes('--daemon') && !args.includes('--tray-only')) {
    toggleOverlay();
  }
}

init();
app.on('window-all-closed', e => e.preventDefault());
