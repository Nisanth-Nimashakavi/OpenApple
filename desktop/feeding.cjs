'use strict';
class FeedCoordinator {
  constructor(dependencies) {
    Object.assign(this, dependencies);
    this.busy = false;
  }
  async decide(message) {
    if (this.busy) throw new Error('An apple is already being handled');
    const { backend, reviews, delivery, targets, window, showRequest } = this;
    if (!reviews.current || reviews.current.id !== message.id)
      throw new Error('This review is no longer active');
    this.busy = true;
    try {
      const current = reviews.current;
      const target = current && targets.get(current.id);
      if (message.outcome === 'approved' && current?.source !== 'mcp' && target) {
        window.hide();
        try {
          await delivery.prepare(target);
        } catch (error) {
          await showRequest(current, 1);
          throw error;
        }
      }
      let result = await reviews.decide(message.id, message.outcome, message.note || '');
      if (result.state === 'approved') {
        window.showInactive?.();
        this.onCommitted?.();
      }
      if (result.state === 'approved' && target) {
        if (this.onCommitted) await new Promise((resolve) => setTimeout(resolve, 380));
        window.hide();
        result = await backend.call('delivery', { request_id: result.id, status: 'sending' });
        try {
          await delivery.prepare(target);
          await delivery.send(target, result.variety, result.note);
          result = await backend.call('delivery', { request_id: result.id, status: 'sent' });
        } catch (error) {
          result = await backend.call('delivery', { request_id: result.id, status: 'failed' });
          result.deliveryError = error.message;
        }
      }
      targets.delete(result.id);

      return result;
    } finally {
      this.busy = false;
    }
  }
}
module.exports = { FeedCoordinator };
