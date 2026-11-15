#!/usr/bin/env node
'use strict';
const { spawn } = require('node:child_process');
const { pythonBinary, bootstrap, rememberDesktop, root } = require('../desktop/runtime.cjs');
const args = process.argv.slice(2);
if (args[0] === '--version') {
  console.log(require('../package.json').version);
  return;
}
if (args[0] === '--help' || args[0] === '-h') {
  console.log(
    'OpenApple — human-reviewed rewards\n\nUsage: openapple [setup|install|uninstall|feed|status|doctor|overlay|gui|button|serve] [options]\n\nRun openapple setup [all|claude|agy|codex] to install the Python backend.\nUse openapple COMMAND --help for command options after setup.',
  );
  return;
}
const desktopArgs = new Set(['--tray-only', '--daemon']);
const command = args[0];

try {
  if (args.length && !desktopArgs.has(command)) {
    const python =
      command === 'setup' && !args.includes('--dry-run') ? bootstrap() : pythonBinary();
    const child = spawn(python, ['-m', 'openapple.cli', ...args], {
      cwd: root,
      stdio: 'inherit',
      env: { ...process.env, OPENAPPLE_DESKTOP_DIR: root },
    });
    child.on('error', (error) => {
      console.error(`OpenApple: ${error.message}. Run openapple setup first.`);
      process.exitCode = 1;
    });
    child.on('exit', (code, signal) => {
      process.exitCode = signal ? 1 : (code ?? 1);
    });
  } else {
    rememberDesktop();
    const electron = require('electron');
    if (typeof electron !== 'string')
      throw new Error('Electron runtime is unavailable; run npm install');
    // Keep the launcher alive so startup failure has an observable exit status.
    const child = spawn(electron, [root, ...args], { stdio: 'inherit', windowsHide: true });
    child.on('error', (error) => {
      console.error(`OpenApple: ${error.message}`);
      process.exitCode = 1;
    });
    child.on('exit', (code, signal) => {
      process.exitCode = signal ? 1 : (code ?? 1);
    });
  }
} catch (error) {
  console.error(`OpenApple: ${error.message}`);
  process.exitCode = 1;
}
