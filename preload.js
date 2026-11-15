const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('bridge', {
  feedApple: (id) => ipcRenderer.invoke('decision', { id, outcome: 'approved' }),
  dropApple: (id) => ipcRenderer.invoke('decision', { id, outcome: 'cancelled' }),
  hideOverlay: () => ipcRenderer.send('hide-overlay'),
  reportError: (message) => ipcRenderer.send('renderer-error', String(message)),
  onSpawnApple: (fn) => ipcRenderer.on('review', (_, data) => fn(data)),
  onFed: (fn) => ipcRenderer.on('fed', () => fn()),
  onDropApple: (fn) => ipcRenderer.on('drop-apple', () => fn()),
  onDismiss: (fn) => ipcRenderer.on('dismiss', () => fn()),
});
