'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const directory = process.env.OPENAPPLE_DATA_DIR || path.join(os.homedir(), '.openapple');
const runtimePython = path.join(
  directory,
  'runtime',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
);

function pythonBinary() {
  if (process.env.OPENAPPLE_PYTHON) return process.env.OPENAPPLE_PYTHON;
  if (fs.existsSync(runtimePython)) return runtimePython;
  return process.platform === 'win32' ? 'python' : 'python3';
}
function run(command, args, options = {}) {
  return execFileSync(command, args, { cwd: root, stdio: 'inherit', ...options });
}
function bootstrap() {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  if (!fs.existsSync(runtimePython)) {
    let python = pythonBinary();
    if (process.platform === 'win32' && !process.env.OPENAPPLE_PYTHON) {
      try {
        execFileSync(python, ['--version'], { stdio: 'ignore' });
      } catch {
        python = 'py';
      }
    }
    run(python, ['-c', 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"']);
    run(python, ['-m', 'venv', path.join(directory, 'runtime')]);
  }
  run(runtimePython, ['-m', 'pip', 'install', '--disable-pip-version-check', root]);
  rememberDesktop();
  return runtimePython;
}
function rememberDesktop() {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const temporary = path.join(directory, `desktop-${process.pid}.tmp`);
  fs.writeFileSync(temporary, JSON.stringify({ root }), { mode: 0o600 });
  fs.renameSync(temporary, path.join(directory, 'desktop.json'));
}
module.exports = { pythonBinary, bootstrap, rememberDesktop, root };
