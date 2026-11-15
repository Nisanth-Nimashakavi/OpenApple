'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ChatDelivery, agentFor } = require('../desktop/delivery.cjs');
const chat = {
  address: '0x123',
  class: 'kitty',
  pid: 123,
  title: 'Codex — OpenApple',
  mapped: true,
};
function fixture() {
  const calls = [];
  let active = { ...chat };
  let afterTyping = null;
  const delivery = new ChatDelivery({
    platform: 'linux',
    environment: { HYPRLAND_INSTANCE_SIGNATURE: 'test' },
    run: async (command, args) => {
      calls.push({ command, args });
      if (command === 'hyprctl' && args.includes('clients'))
        return { stdout: JSON.stringify([chat]) };
      if (command === 'hyprctl' && args.includes('activewindow'))
        return { stdout: JSON.stringify(active) };
      if (command === 'wtype' && args[0] === '--' && afterTyping) active = afterTyping;
      return { stdout: '' };
    },
  });
  return {
    delivery,
    calls,
    setActive(value) {
      active = value;
    },
    afterTyping(value) {
      afterTyping = value;
    },
  };
}

test('recipient detection does not infer an agent from an unrelated window', () => {
  assert.equal(agentFor({ class: 'firefox', title: 'YouTube' }), null);
  assert.equal(agentFor({ class: 'kitty', title: 'zsh' }), null);
  assert.equal(agentFor({ class: 'unknown-app', title: 'Codex notes' }), null);
  assert.equal(agentFor(chat), 'Codex');
  assert.equal(agentFor({ class: 'claude', title: 'A conversation' }), null);
  assert.equal(agentFor({ class: 'firefox', title: 'Codex' }), null);
});

test('manual feed identifies one recipient and sends a request for a chat reaction', async () => {
  const { delivery, calls } = fixture();
  const target = await delivery.focused();
  assert.equal(target.agent, 'Codex');
  assert.match(target.label, /OpenApple/);
  await delivery.prepare(target);
  const receipt = await delivery.send(target, 'Fuji');
  assert.equal(receipt.status, 'sent');
  const typing = calls.find((call) => call.command === 'wtype' && call.args[0] === '--');
  assert.match(typing.args[1], /Fuji, Codex/);
  assert.match(typing.args[1], /short, playful reaction/);
  assert.deepEqual(calls.at(-1), { command: 'wtype', args: ['-k', 'Return'] });
});

test('a changed tab/title aborts before any typing', async () => {
  const { delivery, calls, setActive } = fixture();
  const target = await delivery.focused();
  setActive({ ...chat, title: 'Other chat' });
  await assert.rejects(delivery.send(target, 'Honeycrisp'), /Focus changed/);
  assert.ok(!calls.some((call) => call.command === 'wtype'));
});

test('focus switching while typing prevents submission into the new window', async () => {
  const { delivery, calls, afterTyping } = fixture();
  const target = await delivery.focused();
  afterTyping({ ...chat, address: '0xother' });
  await assert.rejects(delivery.send(target, 'Honeycrisp'), /not submitted/);
  assert.ok(!calls.some((call) => call.command === 'wtype' && call.args[0] === '-k'));
});

test('unsupported desktops do not receive blind global input', async () => {
  const delivery = new ChatDelivery({
    platform: 'linux',
    environment: { WAYLAND_DISPLAY: 'wayland-1' },
  });
  assert.deepEqual(await delivery.list(), []);
  assert.equal(await delivery.focused(), null);
  await assert.rejects(delivery.prepare(chat), /unavailable/);
});

test('overlay positioning affects only the feeder owned by this process', async () => {
  const { delivery, calls } = fixture();
  await delivery.positionOverlay(999, 'OpenApple feeder', {
    x: 0,
    y: 0,
    width: 1920,
    height: 1080,
  });
  assert.ok(!calls.some((call) => call.args[0] === 'dispatch'));
  await delivery.positionOverlay(chat.pid, chat.title, { x: 0, y: 0, width: 1920, height: 1080 });
  const dispatches = calls.filter((call) => call.args[0] === 'dispatch');
  assert.deepEqual(
    dispatches.map((call) => call.args[1]),
    ['setfloating', 'resizewindowpixel', 'movewindowpixel'],
  );
  assert.ok(dispatches.every((call) => call.args[2].includes('address:0x123')));
});

test('terminal inference requires one TTY and a foreground agent', () => {
  const { terminalAgent } = require('../desktop/delivery.cjs');
  const foreground = '100 123 zsh pts/1 Ss zsh\n101 100 codex pts/1 Sl+ codex';
  assert.equal(terminalAgent(123, foreground), 'Codex');
  assert.equal(terminalAgent(123, foreground.replace('Sl+', 'Sl')), null);
  assert.equal(terminalAgent(123, foreground + '\n102 123 zsh pts/2 Ss+ zsh'), null);
  assert.equal(terminalAgent(123, '100 123 zsh pts/1 Ss+ zsh\n101 100 codex ? Sl codex'), null);
});

test('typed rewards stay on one commented line if a terminal is mistakenly selected', async () => {
  const { delivery, calls } = fixture();
  const target = await delivery.focused();
  await delivery.send(target, 'Fuji\nwrong', 'Nice fix\r\nDo it again');
  const message = calls.find((call) => call.command === 'wtype').args[1];
  assert.ok(message.startsWith('# '));
  assert.ok(!/[\r\n]/.test(message));
  assert.match(message, /Nice fix/);
});

test('X11 discovers terminal identity and sends literal Unicode arguments', async () => {
  const calls = [];
  const delivery = new ChatDelivery({
    platform: 'linux',
    environment: { DISPLAY: ':99' },
    run: async (command, args) => {
      calls.push({ command, args });
      const values = {
        getactivewindow: '123\n',
        search: '123\n',
        getwindowpid: '42\n',
        getwindowclassname: 'kitty\n',
        getwindowname: 'Codex\n',
      };
      return { stdout: values[args[0]] || '' };
    },
  });
  const target = await delivery.focused();
  await delivery.prepare(target);
  await delivery.send(target, 'Fuji', 'literal $() `text`');
  assert.equal(target.pid, 42);
  assert.match(calls.find((c) => c.args[0] === 'type').args.at(-1), /literal \$\(\) `text`/);
  assert.deepEqual(calls.at(-1).args, ['key', '--clearmodifiers', 'Return']);
});

for (const platform of ['darwin', 'win32']) {
  test(`${platform} helper protocol keeps message data separate from executable code`, async () => {
    const calls = [];
    const targetWindow = { ...chat, class: platform === 'darwin' ? 'terminal' : 'windowsterminal' };
    const delivery = new ChatDelivery({
      platform,
      environment: {},
      run: async (command, args) => {
        calls.push({ command, args });
        const action = args.at(-2);
        return {
          stdout:
            action === 'list'
              ? JSON.stringify([targetWindow])
              : action === 'active'
                ? JSON.stringify(targetWindow)
                : '',
        };
      },
    });
    const target = await delivery.focused();
    await delivery.prepare(target);
    await delivery.send(target, 'Honeycrisp', 'hello " 🍎');
    const data = calls.find((c) => c.args.at(-2) === 'type').args.at(-1);
    const message = platform === 'win32' ? Buffer.from(data, 'base64').toString('utf8') : data;
    assert.match(message, /hello " 🍎/);
    assert.equal(calls.at(-1).args.at(-2), 'enter');
  });
}

test('missing delivery utility surfaces the error without typing', async () => {
  const delivery = new ChatDelivery({
    platform: 'linux',
    environment: { DISPLAY: ':99' },
    run: async () => {
      throw new Error('xdotool not found');
    },
  });
  await assert.rejects(delivery.focused(), /xdotool not found/);
});

test('stale and concurrent feed decisions cannot focus or award twice', async () => {
  const { FeedCoordinator } = require('../desktop/feeding.cjs');
  let release;
  const wait = new Promise((resolve) => {
    release = resolve;
  });
  let prepared = 0,
    awarded = 0;
  const current = { id: 'one', source: 'desktop' };
  const coordinator = new FeedCoordinator({
    reviews: {
      current,
      decide: async () => {
        awarded++;
        return { id: 'one', state: 'cancelled' };
      },
    },
    delivery: {
      prepare: async () => {
        prepared++;
        await wait;
      },
    },
    targets: new Map([['one', {}]]),
    window: { hide() {} },
  });
  await assert.rejects(
    coordinator.decide({ id: 'stale', outcome: 'approved' }),
    /no longer active/,
  );
  assert.equal(prepared, 0);
  const first = coordinator.decide({ id: 'one', outcome: 'approved' });
  await assert.rejects(coordinator.decide({ id: 'one', outcome: 'approved' }), /already/);
  release();
  await first;
  assert.equal(awarded, 1);
});

test('automatic targeting uses a matching focused agent or a recognized recent terminal', async () => {
  const { delivery } = fixture();
  assert.equal((await delivery.automatic()).agent, 'Codex');
  assert.equal(await delivery.automatic('Claude'), null);
  delivery.focused = async () => null;
  assert.equal((await delivery.automatic()).agent, 'Codex');
  delivery.list = async () => [{ agent: null, title: 'shell' }];
  assert.equal(await delivery.automatic(), null);
});

test('delivery failures retain approval and record failure without replay', async () => {
  const { FeedCoordinator } = require('../desktop/feeding.cjs');
  let sent = 0;
  const statuses = [];
  const result = { id: 'one', state: 'approved', variety: 'Fuji' };
  const reviews = {
    current: { id: 'one', source: 'desktop' },
    decide: async () => {
      reviews.current = null;
      return result;
    },
  };
  const coordinator = new FeedCoordinator({
    reviews,
    targets: new Map([['one', {}]]),
    window: { hide() {}, setFocusable() {}, setIgnoreMouseEvents() {}, showInactive() {} },
    delivery: {
      prepare: async () => {},
      send: async () => {
        sent++;
        throw new Error('Input denied');
      },
    },
    backend: {
      call: async (_, args) => {
        statuses.push(args.status);
        return { ...result, delivery_status: args.status };
      },
    },
  });
  const receipt = await coordinator.decide({ id: 'one', outcome: 'approved' });
  assert.equal(receipt.state, 'approved');
  assert.equal(receipt.delivery_status, 'failed');
  assert.match(receipt.deliveryError, /Input denied/);
  await assert.rejects(coordinator.decide({ id: 'one', outcome: 'approved' }), /no longer active/);
  assert.equal(sent, 1);
  assert.deepEqual(statuses, ['sending', 'failed']);
});

test('no detected agent still permits the original apple gesture without typing', async () => {
  const { FeedCoordinator } = require('../desktop/feeding.cjs');
  let celebrated = 0;
  const feeder = new FeedCoordinator({
    reviews: {
      current: { id: 'one', source: 'desktop' },
      decide: async () => ({ id: 'one', state: 'approved' }),
    },
    targets: new Map(),
    window: {},
    delivery: {
      send: () => {
        throw new Error('Must not type');
      },
    },
    onCommitted: () => celebrated++,
  });
  assert.equal((await feeder.decide({ id: 'one', outcome: 'approved' })).state, 'approved');
  assert.equal(celebrated, 1);
});
