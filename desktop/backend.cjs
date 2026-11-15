'use strict';
const { spawn } = require('node:child_process');
const { EventEmitter } = require('node:events');
const readline = require('node:readline');

class Backend extends EventEmitter {
  constructor(python, options = {}) {
    super();
    this.pending = new Map();
    this.sequence = 0;
    this.failure = null;
    this.diagnostics = '';
    this.child = spawn(python, ['-u', '-m', 'openapple.backend'], {
      ...options,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
    this.child.on('error', (error) => this.fail(error));
    this.child.stdin.on('error', (error) => this.fail(error));
    // close follows stderr EOF, so a startup traceback is available in full.
    this.child.on('close', (code, signal) => {
      const cause = this.diagnostics.trim().split(/\r?\n/).filter(Boolean).at(-1);
      const reason = signal ? `signal ${signal}` : `code ${code}`;
      this.fail(
        new Error(
          `Python backend exited (${reason}).${cause ? `\n${cause}` : ' Restart OpenApple.'}`,
        ),
      );
    });
    this.child.stderr.on('data', (data) => {
      this.diagnostics = (this.diagnostics + data.toString('utf8')).slice(-8192);
      process.stderr.write(data);
    });
    readline.createInterface({ input: this.child.stdout }).on('line', (line) => {
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        this.fail(new Error('Invalid backend protocol'));
        return;
      }
      const pending = this.pending.get(message.id);
      if (!pending) return;
      this.pending.delete(message.id);
      clearTimeout(pending.timer);
      if (message.error) pending.reject(new Error(message.error));
      else pending.resolve(message.result);
    });
  }
  fail(error) {
    if (this.failure) return;
    this.failure = error;
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
    this.emit('fatal', error);
  }
  call(operation, args = {}) {
    if (this.failure) return Promise.reject(this.failure);
    return new Promise((resolve, reject) => {
      const id = ++this.sequence;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error('Backend operation timed out'));
      }, 12000);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(JSON.stringify({ id, operation, arguments: args }) + '\n');
    });
  }
  close() {
    this.child.stdin.end();
  }
}
module.exports = { Backend };
