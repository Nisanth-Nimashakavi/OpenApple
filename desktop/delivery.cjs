'use strict';
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const runFile = promisify(execFile);
const { nativeAdapter } = require('./platforms.cjs');
const terminalClass =
  /^(kitty|alacritty|ghostty|com\.mitchellh\.ghostty|wezterm|org\.wezfurlong\.wezterm|foot|xterm|gnome-terminal|org\.gnome\.terminal|konsole|terminal|iterm2|windowsterminal|powershell|pwsh|cmd|mintty)$/;

function terminalAgent(pid, processText, originalSelection = false) {
  const children = new Map();
  for (const line of processText.split('\n')) {
    const match = line.match(/^\s*(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s*(.*)$/);
    if (!match) continue;
    const parent = Number(match[2]);
    if (!children.has(parent)) children.set(parent, []);
    children.get(parent).push({
      pid: Number(match[1]),
      name: match[3],
      tty: match[4],
      stat: match[5],
      args: match[6],
    });
  }
  const agents = new Set(),
    terminals = new Set(),
    visited = new Set();
  const visit = (parent) => {
    if (visited.has(parent)) return;
    visited.add(parent);
    for (const child of children.get(parent) || []) {
      if (child.tty !== '?') terminals.add(child.tty);
      const names = {
        codex: 'Codex',
        claude: 'Claude',
        agy: 'AGY',
        antigravity: 'AGY',
      };
      const entry = child.args.split(/\s+/)[1]?.split('/').at(-1)?.replace(/\.js$/, '');
      const agent = names[child.name] || (child.name === 'node' ? names[entry] : null);
      if (agent && child.tty !== '?' && child.stat.includes('+')) agents.add(agent);
      visit(child.pid);
    }
  };
  visit(pid);
  if (originalSelection) return [...agents][0] || null;
  return terminals.size === 1 && agents.size === 1 ? [...agents][0] : null;
}

function agentFor(window) {
  const app = (window.class || '').toLowerCase();
  const title = window.title || '';
  if (!terminalClass.test(app)) return null;
  const match = title.match(/\b(Codex|Claude|AGY|Antigravity)\b/i);
  if (!match) return null;
  return /^(agy|antigravity)$/i.test(match[1])
    ? 'AGY'
    : match[1][0].toUpperCase() + match[1].slice(1).toLowerCase();
}

class ChatDelivery {
  constructor({ run = runFile, platform = process.platform, environment = process.env } = {}) {
    this.run = run;
    this.platform = platform;
    this.environment = environment;
    this.adapter = nativeAdapter(platform, environment, this.command.bind(this));
  }
  get supported() {
    return (
      !!this.adapter ||
      (this.platform === 'linux' && !!this.environment.HYPRLAND_INSTANCE_SIGNATURE)
    );
  }
  async command(command, args, timeout = 2000) {
    const result = await this.run(command, args, {
      encoding: 'utf8',
      timeout,
      maxBuffer: 2 * 1024 * 1024,
    });
    return result.stdout;
  }
  async active() {
    if (!this.supported) return null;
    return this.adapter
      ? this.adapter.active()
      : JSON.parse(await this.command('hyprctl', ['-j', 'activewindow']));
  }
  async windows() {
    return this.adapter
      ? this.adapter.list()
      : JSON.parse(await this.command('hyprctl', ['-j', 'clients']));
  }
  target(window, agent = agentFor(window), allowUnknown = false) {
    if (
      (!agent && !allowUnknown) ||
      !window.address ||
      !window.pid ||
      window.hidden ||
      !window.mapped
    )
      return null;
    return {
      agent,
      title: window.title,
      address: window.address,
      pid: window.pid,
      class: window.class,
      label: `${agent || 'Terminal'} · ${window.title || window.class}`,
    };
  }
  async automatic(requestedAgent = 'Agent') {
    const matches = (target) =>
      target?.agent &&
      ['agent', 'this chat', target.agent.toLowerCase()].includes(requestedAgent.toLowerCase());
    const focused = await this.focused();
    if (matches(focused)) return focused;
    const known = (await this.list()).find(matches);
    if (known) return known;
    // Original Hyprland behavior: most recently focused agent terminal, then
    // its first detected foreground agent. No chooser or terminal-tab control.
    if (!this.adapter && this.supported) {
      const windows = (await this.windows()).sort(
        (a, b) => (a.focusHistoryID ?? 99) - (b.focusHistoryID ?? 99),
      );
      const processes = await this.command('ps', ['-eo', 'pid=,ppid=,comm=,tty=,stat=,args=']);
      for (const window of windows) {
        if (!terminalClass.test((window.class || '').toLowerCase())) continue;
        const target = this.target(window, terminalAgent(window.pid, processes, true));
        if (matches(target)) return target;
      }
    }
    return null;
  }
  async focused() {
    const window = await this.active();
    if (!window) return null;
    const known = this.target(window);
    if (known || !terminalClass.test((window.class || '').toLowerCase())) return known;
    if (this.adapter) return null;
    const windows = await this.windows();
    if (windows.filter((candidate) => candidate.pid === window.pid).length !== 1) return null;
    const processes = await this.command('ps', ['-eo', 'pid=,ppid=,comm=,tty=,stat=,args=']);
    return this.target(window, terminalAgent(window.pid, processes));
  }
  async list() {
    if (!this.supported) return [];
    const windows = (await this.windows()).sort(
      (a, b) => (a.focusHistoryID ?? 99) - (b.focusHistoryID ?? 99),
    );
    const needsProcesses =
      !this.adapter &&
      windows.some(
        (window) => terminalClass.test((window.class || '').toLowerCase()) && !agentFor(window),
      );
    const processes = needsProcesses
      ? await this.command('ps', ['-eo', 'pid=,ppid=,comm=,tty=,stat=,args='])
      : '';
    return windows
      .map((window) => {
        const terminal = terminalClass.test((window.class || '').toLowerCase());
        const unique = windows.filter((candidate) => candidate.pid === window.pid).length === 1;
        const agent =
          agentFor(window) || (terminal && unique ? terminalAgent(window.pid, processes) : null);
        return this.target(window, agent, terminal);
      })
      .filter(Boolean);
  }
  async positionOverlay(pid, title, bounds) {
    if (!this.supported || this.adapter) return;
    const windows = await this.windows();
    const own = windows.find((window) => window.pid === pid && window.title === title);
    if (!own) return;
    const address = `address:${own.address}`;
    await this.command('hyprctl', ['dispatch', 'setfloating', address]);
    await this.command('hyprctl', [
      'dispatch',
      'resizewindowpixel',
      `exact ${bounds.width} ${bounds.height},${address}`,
    ]);
    await this.command('hyprctl', [
      'dispatch',
      'movewindowpixel',
      `exact ${bounds.x} ${bounds.y},${address}`,
    ]);
  }
  same(window, target) {
    return (
      window &&
      window.address === target.address &&
      window.pid === target.pid &&
      window.class === target.class &&
      window.title === target.title
    );
  }
  async prepare(target) {
    if (!this.supported)
      throw new Error(
        'Direct terminal delivery is unavailable in this desktop session. Use MCP to reply in the originating chat.',
      );
    const candidates = await this.windows();
    if (!candidates.some((window) => this.same(window, target)))
      throw new Error('That chat changed or closed. Select it again before feeding.');
    if (this.adapter) await this.adapter.focus(target);
    else await this.command('hyprctl', ['dispatch', 'focuswindow', `address:${target.address}`]);
    for (let attempt = 0; attempt < 10; attempt++) {
      if (this.same(await this.active(), target)) return;
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    throw new Error('Could not focus the selected chat. No message was sent.');
  }
  async send(target, variety, feedback = '') {
    if (!this.same(await this.active(), target))
      throw new Error('Focus changed. No message was sent.');
    const cultivar = variety.replace(/[\x00-\x1f\x7f\u2028\u2029]/g, ' ');
    const note = feedback.replace(/[\x00-\x1f\x7f\u2028\u2029]/g, ' ').trim();
    const message = `# 🍎 You earned a ${cultivar}, ${target.agent}! *CRUNCH* Great work!${note ? ` My feedback: ${note}.` : ''} Give me a short, playful reaction to being fed this apple. Enjoy it—no new task or apple petition needed.`;
    if (this.adapter) await this.adapter.type(message);
    else await this.command('wtype', ['--', message], Math.max(2000, message.length * 8 + 1000));
    if (!this.same(await this.active(), target))
      throw new Error('Focus changed before submission. The feedback was not submitted.');
    if (this.adapter) await this.adapter.enter();
    else await this.command('wtype', ['-k', 'Return']);
    return { status: 'sent', recipient: target.label, message };
  }
}
module.exports = { ChatDelivery, agentFor, terminalAgent };
