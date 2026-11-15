'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const http = require('node:http');
const { Backend } = require('../desktop/backend.cjs');
const { Reviews } = require('../desktop/reviews.cjs');
const { credentials, startBridge } = require('../desktop/bridge.cjs');

function request(options, method, route, data, overrides = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host: '127.0.0.1',
        port: options.port,
        path: route,
        method,
        headers: {
          Authorization: `Bearer ${options.token}`,
          'Content-Type': 'application/json',
          ...overrides,
        },
      },
      (res) => {
        let body = '';
        res.on('data', (chunk) => (body += chunk));
        res.on('end', () => resolve({ code: res.statusCode, body: JSON.parse(body) }));
      },
    );
    req.on('error', reject);
    req.end(data === undefined ? undefined : JSON.stringify(data));
  });
}

function fixture(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'openapple-test-'));
  const backend = new Backend(
    process.env.OPENAPPLE_PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    {
      cwd: path.resolve(__dirname, '..'),
      env: { ...process.env, OPENAPPLE_DATA_DIR: directory },
    },
  );
  t.after(async () => {
    if (backend.child.exitCode === null && backend.child.signalCode === null) {
      const exited = new Promise((resolve) => backend.child.once('exit', resolve));
      backend.close();
      await exited;
    }
    fs.rmSync(directory, { recursive: true, force: true });
  });
  return { directory, backend };
}

test('private backend reports errors without breaking subsequent messages', async (t) => {
  const { backend } = fixture(t);
  assert.equal((await backend.call('health')).protocol, 1);
  await assert.rejects(backend.call('create', { task: '' }));
  assert.equal((await backend.call('snapshot')).total_apples, 0);
  await assert.rejects(backend.call('not-a-command'));
  const row = await backend.call('create', { task: 'Good work' });
  assert.equal((await backend.call('get', { request_id: row.id })).state, 'pending');
});

test('two HTTP clients receive independent committed decisions; retries do not award twice', async (t) => {
  const { backend, directory } = fixture(t);
  const shown = [];
  const reviews = new Reviews(
    backend,
    (row) => shown.push(row.id),
    () => {},
  );
  const options = {
    backend,
    token: credentials(directory),
    port: 0,
    changed: () => reviews.refresh(),
  };
  const server = await startBridge(options);
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const first = {
    task: 'Task A',
    variety: 'Fuji',
    agent: 'codex',
    request_id: crypto.randomUUID(),
  };
  const second = {
    task: 'Task B',
    variety: 'Honeycrisp',
    agent: 'claude',
    request_id: crypto.randomUUID(),
  };
  const results = await Promise.all([
    request(options, 'POST', '/petitions', first),
    request(options, 'POST', '/petitions', second),
  ]);
  assert.deepEqual(
    results.map((r) => r.body.state),
    ['pending', 'pending'],
  );
  assert.equal(shown.length, 1);
  const active = reviews.current.id;
  await assert.rejects(reviews.decide('forged-id', 'approved', ''));
  await reviews.decide(active, 'approved', 'Human checked');
  await assert.rejects(reviews.decide(active, 'approved', 'Replay'));
  await reviews.refresh(); // completion animation holds the next review
  assert.equal(shown.length, 1);
  await reviews.advance();
  assert.equal(shown.length, 2);
  await reviews.decide(reviews.current.id, 'rejected', 'Needs a test');
  for (const original of [first, second])
    assert.equal((await request(options, 'POST', '/petitions', original)).code, 200);
  const state = await backend.call('snapshot');
  assert.equal(state.total_apples, 1);
  assert.equal(state.current_streak, 0);
  assert.equal(state.history.length, 2);
  assert.equal((await request(options, 'GET', `/petitions/${active}`)).body.state, 'approved');
});

test('bridge rejects unauthenticated, wrong-origin, malformed and grant requests', async (t) => {
  const { backend, directory } = fixture(t);
  const options = { backend, token: credentials(directory), port: 0, changed: async () => {} };
  const server = await startBridge(options);
  t.after(() => new Promise((resolve) => server.close(resolve)));
  assert.equal(
    (await request(options, 'GET', '/snapshot', undefined, { Authorization: 'Bearer wrong' })).code,
    401,
  );
  assert.equal(
    (await request(options, 'GET', '/health', undefined, { Origin: 'https://untrusted.invalid' }))
      .code,
    403,
  );
  assert.equal(
    (await request(options, 'GET', '/health', undefined, { Host: 'evil.invalid' })).code,
    403,
  );
  assert.equal((await request(options, 'DELETE', '/petitions')).code, 405);
  assert.equal((await request(options, 'GET', '/feed?task=forged')).code, 400);
  assert.equal(
    (await request(options, 'POST', '/petitions', { task: 'Work', approved: true })).code,
    400,
  );
  assert.equal((await request(options, 'POST', '/approve', {})).code, 404);
  assert.equal(
    (
      await request(options, 'POST', '/petitions', {
        request_id: crypto.randomUUID(),
        task: 'x'.repeat(20000),
      })
    ).code,
    413,
  );
  assert.equal((await backend.call('snapshot')).total_apples, 0);
});

test('HTTP cancellation resolves the correct request without awarding', async (t) => {
  const { backend, directory } = fixture(t);
  const options = { backend, token: credentials(directory), port: 0, changed: async () => {} };
  const server = await startBridge(options);
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const result = await request(options, 'POST', '/petitions', {
    task: 'Cancel',
    request_id: crypto.randomUUID(),
  });
  assert.equal(
    (await request(options, 'POST', `/petitions/${result.body.id}/cancel`, {})).body.state,
    'cancelled',
  );
  assert.equal((await backend.call('snapshot')).total_apples, 0);
});

test('token creation is stable and rejects insecure credentials', (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'openapple-token-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  assert.equal(credentials(directory), credentials(directory));
  fs.writeFileSync(path.join(directory, 'bridge.token'), 'broken');
  assert.throws(() => credentials(directory), /Invalid/);
});

test('backend crash rejects pending and future operations', async (t) => {
  const { backend } = fixture(t);
  await backend.call('health');
  const exited = new Promise((resolve) => backend.child.once('close', resolve));
  backend.child.kill();
  await exited;
  await assert.rejects(backend.call('snapshot'), /exited/);
});

test('backend startup failure carries the actual cause to the desktop', async (t) => {
  const { directory } = fixture(t);
  const failedDirectory = path.join(directory, 'failed');
  fs.mkdirSync(failedDirectory);
  fs.writeFileSync(
    path.join(failedDirectory, 'ledger.json'),
    JSON.stringify({ total_apples: 3, history: [] }),
  );
  const failing = new Backend(
    process.env.OPENAPPLE_PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    {
      cwd: path.resolve(__dirname, '..'),
      env: { ...process.env, OPENAPPLE_DATA_DIR: failedDirectory },
    },
  );
  t.after(() => failing.close());
  await assert.rejects(failing.call('health'), /Legacy totals disagree with history/);
});
