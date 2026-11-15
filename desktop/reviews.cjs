'use strict';

class Reviews {
  constructor(backend, show, dismiss) {
    this.backend = backend;
    this.show = show;
    this.dismiss = dismiss;
    this.current = null;
    this.paused = false;
    this.serial = Promise.resolve();
  }
  refresh() {
    this.serial = this.serial
      .catch(() => {})
      .then(async () => {
        if (this.paused) return;
        const queue = await this.backend.call('pending');
        if (this.current && !queue.some((row) => row.id === this.current.id)) {
          this.current = null;
          this.dismiss();
        }
        if (!this.current && queue.length) {
          this.current = queue[0];
          await this.show(this.current, queue.length);
        }
      });
    return this.serial;
  }
  advance() {
    this.paused = false;
    return this.refresh();
  }
  decide(id, outcome, note) {
    this.serial = this.serial
      .catch(() => {})
      .then(async () => {
        if (!this.current || this.current.id !== id)
          throw new Error('This review is no longer active');
        const result = await this.backend.call('decide', { request_id: id, outcome, note });
        this.current = null;
        this.paused = true;
        return result;
      });
    return this.serial;
  }
}
module.exports = { Reviews };
