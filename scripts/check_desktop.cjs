const fs = require('node:fs');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { spawn } = require('node:child_process');
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'openapple-electron-'));
let base, token, app;
async function freePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}
async function until(check) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    try {
      if (await check()) return;
    } catch {}
    await pause(100);
  }
  throw new Error('Electron did not reach the expected state within 20 seconds');
}
async function api(method, route, body) {
  const response = await fetch(base + route, {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  assert.equal(response.status, 200, JSON.stringify(data));
  return data;
}
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  if (process.platform !== 'linux')
    throw new Error(
      'This headless renderer check is Linux-only; use the native checklist on other platforms',
    );
  const port = await freePort(),
    debugPort = await freePort();
  base = `http://127.0.0.1:${port}`;
  // Stub OS input inside this test process: no test can type into a real application.
  const fakeBin = path.join(directory, 'bin');
  fs.mkdirSync(fakeBin);
  const chat = {
    address: '0xtest',
    pid: 123,
    class: 'kitty',
    title: 'Codex — Project terminal',
    mapped: true,
  };
  fs.writeFileSync(
    path.join(fakeBin, 'hyprctl'),
    '#!/usr/bin/env node\nconst chat=' +
      JSON.stringify(chat) +
      ";process.stdout.write(JSON.stringify(process.argv.includes('clients')?[chat]:chat));",
    { mode: 0o755 },
  );
  fs.writeFileSync(path.join(fakeBin, 'ps'), '#!/usr/bin/env node\n', { mode: 0o755 });
  fs.writeFileSync(
    path.join(fakeBin, 'wtype'),
    "#!/usr/bin/env node\nrequire('fs').appendFileSync(process.env.OPENAPPLE_DELIVERY_LOG,JSON.stringify(process.argv.slice(2))+'\\n');",
    { mode: 0o755 },
  );
  app = spawn(
    require('electron'),
    [
      path.resolve(__dirname, '..'),
      '--tray-only',
      '--ozone-platform=headless',
      '--no-sandbox',
      `--remote-debugging-port=${debugPort}`,
    ],
    {
      env: {
        ...process.env,
        OPENAPPLE_DATA_DIR: directory,
        OPENAPPLE_PORT: String(port),
        OPENAPPLE_SOUND: '0',
        HYPRLAND_INSTANCE_SIGNATURE: 'isolated-test',
        PATH: fakeBin + path.delimiter + process.env.PATH,
        OPENAPPLE_DELIVERY_LOG: path.join(directory, 'typed.jsonl'),
      },
      stdio: ['ignore', 'ignore', 'pipe'],
    },
  );
  let logs = '';
  app.stderr.on('data', (chunk) => (logs = (logs + chunk).slice(-4000)));
  app.on('error', (error) => (logs += error.message));
  await until(async () => {
    token = fs.readFileSync(path.join(directory, 'bridge.token'), 'utf8').trim();
    return (await api('GET', '/health')).protocol === 1;
  }).catch((error) => {
    throw new Error(error.message + '\n' + logs);
  });
  assert.equal((await api('GET', '/health')).application, 'openapple');
  const targets = await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json();
  const target = targets.find((t) => t.url.endsWith('/overlay.html'));
  assert.ok(target, 'renderer target');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r, { once: true }));
  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (event) => {
    const m = JSON.parse(event.data);
    if (pending.has(m.id)) {
      pending.get(m.id)(m);
      pending.delete(m.id);
    }
  });
  async function evaluate(expression) {
    const n = ++id;
    const response = new Promise((r) => pending.set(n, r));
    ws.send(
      JSON.stringify({
        id: n,
        method: 'Runtime.evaluate',
        params: { expression, returnByValue: true, awaitPromise: true },
      }),
    );
    const m = await response;
    assert.ok(!m.result.exceptionDetails, JSON.stringify(m));
    return m.result.result.value;
  }
  assert.equal(await evaluate('typeof window.bridge.feedApple'), 'function');
  const first = await api('POST', '/petitions', {
    request_id: crypto.randomUUID(),
    source: 'mcp',
    task: 'Electron smoke approval',
    agent: 'codex',
    variety: 'Fuji',
  });
  const second = await api('POST', '/petitions', {
    request_id: crypto.randomUUID(),
    source: 'mcp',
    task: 'Electron smoke rejection',
    agent: 'claude',
    variety: 'Honeycrisp',
  });
  await pause(150);
  assert.equal(await evaluate('currentDetails.task'), first.task);
  assert.equal((await api('GET', '/snapshot')).total_apples, 0);
  await evaluate(
    "document.getElementById('c').dispatchEvent(new MouseEvent('mousemove',{clientX:430,clientY:220,bubbles:true}))",
  );
  await until(async () => Math.abs((await evaluate('apple.x')) - 430) < 3);
  await evaluate(
    "document.getElementById('c').dispatchEvent(new MouseEvent('mousedown',{button:0,bubbles:true}))",
  );
  await until(async () => (await api('GET', `/petitions/${first.id}`)).state === 'approved');
  await until(async () => (await evaluate('currentDetails.task')) === second.task);
  await evaluate('cancel()');
  await until(async () => (await api('GET', `/petitions/${second.id}`)).state === 'cancelled');
  const third = await api('POST', '/petitions', {
    request_id: crypto.randomUUID(),
    source: 'mcp',
    task: 'Electron smoke cancel',
    agent: 'Agent',
    variety: 'Golden Delicious',
  });
  await until(async () => (await evaluate('currentDetails.task')) === third.task);
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))");
  await until(async () => (await api('GET', `/petitions/${third.id}`)).state === 'cancelled');
  assert.equal((await api('GET', `/petitions/${third.id}`)).state, 'cancelled');
  const state = await api('GET', '/snapshot');
  assert.equal(state.total_apples, 1);
  assert.equal(state.current_streak, 1);
  assert.equal(state.history.length, 3);
  await until(async () => await evaluate("apple.state === 'idle'"));
  // A CLI/manual feed must attach to the visible chat and request an AI reaction.
  const manual = await api('POST', '/petitions', {
    request_id: crypto.randomUUID(),
    task: 'Manual reward',
    agent: 'Agent',
    variety: 'Honeycrisp',
  });
  await until(async () => (await evaluate('currentDetails.task')) === manual.task);
  assert.equal(await evaluate('currentAgent'), 'CODEX');
  assert.equal(
    await evaluate(
      "document.querySelector('main, section, button, select, textarea, details') === null",
    ),
    true,
  );
  assert.match(await evaluate('currentDetails.recipient'), /Project terminal/);
  if (process.env.OPENAPPLE_SCREENSHOT) {
    const metricsId = ++id;
    const metrics = new Promise((resolve) => pending.set(metricsId, resolve));
    ws.send(
      JSON.stringify({
        id: metricsId,
        method: 'Emulation.setDeviceMetricsOverride',
        params: { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false },
      }),
    );
    await metrics;
    await pause(150);
    const screenshotId = ++id;
    const response = new Promise((resolve) => pending.set(screenshotId, resolve));
    ws.send(
      JSON.stringify({
        id: screenshotId,
        method: 'Page.captureScreenshot',
        params: { format: 'png' },
      }),
    );
    const capture = await response;
    fs.writeFileSync(process.env.OPENAPPLE_SCREENSHOT, Buffer.from(capture.result.data, 'base64'));
  }
  await evaluate('feed()');
  await until(async () => (await api('GET', `/petitions/${manual.id}`)).delivery_status === 'sent');
  const typed = fs.readFileSync(path.join(directory, 'typed.jsonl'), 'utf8');
  assert.match(typed, /short, playful reaction/);
  assert.match(typed, /Honeycrisp, Codex/);
  assert.equal((await api('GET', '/snapshot')).total_apples, 2);
  await until(async () => await evaluate("apple.state === 'idle'"));
  const mcpProgram = `
import anyio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    params=StdioServerParameters(command=sys.executable,args=['-m','openapple.server'],env=dict(os.environ))
    async with stdio_client(params) as (reader,writer), ClientSession(reader,writer) as session:
        await session.initialize()
        response=await session.call_tool('petition_for_apple',{'task_summary':'MCP chat reward','agent_name':'Codex','variety':'Cosmic Crisp'})
        print(json.dumps([block.text for block in response.content if hasattr(block,'text')]),flush=True)
anyio.run(main)
`;
  const mcpClient = spawn(process.env.OPENAPPLE_PYTHON || 'python3', ['-c', mcpProgram], {
    cwd: path.resolve(__dirname, '..'),
    env: {
      ...process.env,
      OPENAPPLE_DATA_DIR: directory,
      OPENAPPLE_PORT: String(port),
      OPENAPPLE_HEADLESS: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let toolResponse = '',
    clientErrors = '';
  mcpClient.stdout.on('data', (chunk) => (toolResponse += chunk));
  mcpClient.stderr.on('data', (chunk) => (clientErrors += chunk));
  const clientDone = new Promise((resolve) => mcpClient.once('close', (code) => resolve(code)));
  try {
    await until(async () => (await evaluate('currentDetails.task')) === 'MCP chat reward');
    assert.equal(await evaluate('currentDetails.delivery'), 'mcp');
    await evaluate('feed()');
    assert.equal(await clientDone, 0, clientErrors);
    assert.match(toolResponse, /for YOU, Codex/);
    assert.match(toolResponse, /next message in this conversation/);
    assert.match(toolResponse, /Cosmic Crisp/);
    const finalState = await api('GET', '/snapshot');
    assert.equal(finalState.total_apples, 3);
    assert.equal(finalState.history.at(-1).delivery_status, 'mcp');
  } finally {
    if (mcpClient.exitCode === null) mcpClient.kill();
  }
  console.log(
    'Actual Electron: cursor feeder, named manual recipient with stubbed chat input, and real MCP reward-to-chat response passed.',
  );
  ws.close();
})()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    if (app && app.exitCode === null && app.signalCode === null) {
      const done = new Promise((resolve) => app.once('close', resolve));
      app.kill();
      await done;
    }
    fs.rmSync(directory, { recursive: true, force: true });
  });
