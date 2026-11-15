'use strict';
const http = require('node:http');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

function credentials(directory) {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const filename = path.join(directory, 'bridge.token');
  try {
    fs.writeFileSync(filename, crypto.randomBytes(32).toString('hex'), { flag: 'wx', mode: 0o600 });
  } catch (error) {
    if (error.code !== 'EEXIST') throw error;
  }
  const info = fs.lstatSync(filename);
  if (!info.isFile() || info.isSymbolicLink())
    throw new Error('Bridge credentials must be a regular file');
  if (process.platform !== 'win32' && (info.uid !== process.getuid() || info.mode & 0o077)) {
    throw new Error('Bridge credentials must be owned by you and have mode 0600');
  }
  const token = fs.readFileSync(filename, 'utf8').trim();
  if (!/^[a-f0-9]{64}$/.test(token)) throw new Error('Invalid bridge credentials');
  return token;
}

function handler(options) {
  return async (req, res) => {
    const { backend, token, port, changed } = options;
    const send = (status, body) => {
      if (!res.destroyed) {
        res.writeHead(status, {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-store',
          'X-Content-Type-Options': 'nosniff',
        });
        res.end(JSON.stringify(body));
      }
    };
    try {
      if (req.headers.host !== `127.0.0.1:${port}` || req.headers.origin) {
        send(403, { error: 'Invalid origin or host' });
        return;
      }
      const actual = Buffer.from(req.headers.authorization || '');
      const expected = Buffer.from(`Bearer ${token}`);
      if (actual.length !== expected.length || !crypto.timingSafeEqual(actual, expected)) {
        send(401, { error: 'Authentication required' });
        return;
      }
      const url = new URL(req.url, `http://127.0.0.1:${port}`);
      if (url.search) {
        send(400, { error: 'Query parameters are not supported' });
        return;
      }
      const match = url.pathname.match(/^\/petitions\/([a-f0-9-]{36})(\/(?:cancel|received))?$/i);
      if (!['/health', '/snapshot', '/petitions'].includes(url.pathname) && !match) {
        send(404, { error: 'Unknown route' });
        return;
      }
      const expectedMethod = url.pathname === '/petitions' || match?.[2] ? 'POST' : 'GET';
      if (req.method !== expectedMethod) {
        res.setHeader('Allow', expectedMethod);
        send(405, { error: 'Method not allowed' });
        return;
      }
      if (req.method === 'GET') {
        if (url.pathname === '/health') {
          send(200, await backend.call('health'));
          return;
        }
        if (url.pathname === '/snapshot') {
          send(200, await backend.call('snapshot'));
          return;
        }
        send(200, await backend.call('get', { request_id: match[1] }));
        return;
      }
      if (req.headers['content-type'] !== 'application/json') {
        send(415, { error: 'Expected application/json' });
        return;
      }
      const chunks = [];
      let bytes = 0;
      for await (const chunk of req) {
        bytes += chunk.length;
        if (bytes > 16384) {
          send(413, { error: 'Payload too large' });
          return;
        }
        chunks.push(chunk);
      }
      const data = JSON.parse(
        new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks)),
      );
      if (!data || Array.isArray(data) || typeof data !== 'object')
        throw new Error('Expected a JSON object');
      if (match?.[2]) {
        if (Object.keys(data).length) throw new Error('Cancel body must be empty');
        const result =
          match[2] === '/received'
            ? await backend.call('delivery', { request_id: match[1], status: 'mcp' })
            : await backend.call('decide', { request_id: match[1], outcome: 'cancelled' });
        await changed();
        send(200, result);
        return;
      }
      const allowed = new Set(['task', 'agent', 'variety', 'request_id', 'ttl', 'source']);
      if (Object.keys(data).some((key) => !allowed.has(key)))
        throw new Error('Unknown petition field');
      if (!data.request_id) throw new Error('request_id is required for retry safety');
      const source = data.source === 'mcp' ? 'mcp' : 'client';
      const result = await backend.call('create', { ...data, source });
      await changed();
      send(200, result);
    } catch (error) {
      send(400, { error: error.message });
    }
  };
}

async function startBridge(options) {
  const server = http.createServer(handler(options));
  server.requestTimeout = 5000;
  server.headersTimeout = 5000;
  server.maxHeadersCount = 20;
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(options.port, '127.0.0.1', resolve);
  });
  options.port = server.address().port;
  return server;
}
module.exports = { credentials, handler, startBridge };
