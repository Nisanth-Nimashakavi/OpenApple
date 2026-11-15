'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
function check(entry) {
  const filename = path.join(root, entry);
  if (fs.statSync(filename).isDirectory()) {
    for (const name of fs.readdirSync(filename)) check(path.join(entry, name));
  } else if (/\.(?:c?js)$/.test(filename))
    execFileSync(process.execPath, ['--check', filename], { stdio: 'inherit' });
}
for (const entry of ['main.js', 'overlay.js', 'preload.js', 'desktop', 'bin', 'scripts'])
  check(entry);
