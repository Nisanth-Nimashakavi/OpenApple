#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
command -v node >/dev/null || { echo 'Node.js 22+ is required' >&2; exit 1; }
command -v npm >/dev/null || { echo 'npm is required' >&2; exit 1; }
npm ci
node bin/openapple.js setup "$@"
echo 'Setup complete. Run node bin/openapple.js (or npm install -g . for the openapple command).'
