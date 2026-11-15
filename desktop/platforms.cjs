'use strict';
const path = require('node:path');

function nativeAdapter(platform, environment, command) {
  if (
    platform === 'linux' &&
    !environment.WAYLAND_DISPLAY &&
    !environment.HYPRLAND_INSTANCE_SIGNATURE &&
    environment.DISPLAY
  ) {
    const xdo = (...args) => command('xdotool', args);
    const inspect = async (id) => {
      id = id.trim();
      if (!/^\d+$/.test(id)) return null;
      const [pid, app, title] = await Promise.all([
        xdo('getwindowpid', id),
        xdo('getwindowclassname', id),
        xdo('getwindowname', id),
      ]);
      return {
        address: id,
        pid: Number(pid.trim()),
        class: app.trim().toLowerCase(),
        title: title.trim(),
        mapped: true,
      };
    };
    return {
      active: async () => inspect(await xdo('getactivewindow')),
      list: async () => {
        const ids = (await xdo('search', '--onlyvisible', '--name', '.')).trim().split(/\s+/);
        return (await Promise.all(ids.map((id) => inspect(id).catch(() => null)))).filter(Boolean);
      },
      focus: (target) => xdo('windowactivate', '--sync', target.address),
      type: (message) =>
        command(
          'xdotool',
          ['type', '--clearmodifiers', '--delay', '1', '--', message],
          Math.max(2000, message.length * 8 + 1000),
        ),
      enter: () => xdo('key', '--clearmodifiers', 'Return'),
    };
  }
  if (!['darwin', 'win32'].includes(platform)) return null;
  const invoke = async (action, value = '') => {
    if (platform === 'darwin')
      return command(
        'osascript',
        ['-l', 'JavaScript', path.join(__dirname, 'native', 'macos.js'), action, value],
        10000,
      );
    return command(
      'powershell.exe',
      [
        '-NoProfile',
        '-NonInteractive',
        '-File',
        path.join(__dirname, 'native', 'windows.ps1'),
        action,
        Buffer.from(value, 'utf8').toString('base64'),
      ],
      10000,
    );
  };
  return {
    active: async () => JSON.parse(await invoke('active')),
    list: async () => JSON.parse(await invoke('list')),
    focus: (target) => invoke('focus', JSON.stringify(target)),
    type: (message) => invoke('type', message),
    enter: () => invoke('enter'),
  };
}
module.exports = { nativeAdapter };
