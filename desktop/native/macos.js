/* Executed by osascript's JavaScript for Automation, never by Electron. */
function run(argv) {
  const events = Application('System Events');
  const action = argv[0];
  const names = {
    Terminal: 'terminal',
    iTerm2: 'iterm2',
    kitty: 'kitty',
    Alacritty: 'alacritty',
    Ghostty: 'ghostty',
    WezTerm: 'wezterm',
  };
  const records = () => {
    const result = [];
    for (const process of events.applicationProcesses()) {
      const name = process.name();
      if (!names[name]) continue;
      const pid = process.unixId();
      for (const window of process.windows()) {
        result.push({
          address: String(pid) + ':' + String(window.id()),
          pid,
          class: names[name],
          title: window.name(),
          mapped: true,
        });
      }
    }
    return result;
  };
  if (action === 'list') return JSON.stringify(records());
  if (action === 'active') {
    const process = events.applicationProcesses.whose({ frontmost: true })()[0];
    if (!process || !names[process.name()] || !process.windows.length) return 'null';
    const pid = process.unixId();
    const window = process.windows[0];
    return JSON.stringify({
      address: String(pid) + ':' + String(window.id()),
      pid,
      class: names[process.name()],
      title: window.name(),
      mapped: true,
    });
  }
  if (action === 'focus') {
    const target = JSON.parse(argv[1]);
    const process = events.applicationProcesses.whose({ unixId: target.pid })()[0];
    if (!process) throw new Error('Terminal closed');
    process.frontmost = true;
    const window = process
      .windows()
      .find((w) => String(target.pid) + ':' + String(w.id()) === target.address);
    if (!window) throw new Error('Terminal window closed');
    window.actions.byName('AXRaise').perform();
  } else if (action === 'type') events.keystroke(argv[1]);
  else if (action === 'enter') events.keyCode(36);
  else throw new Error('Unknown delivery action');
  return '';
}
