const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('bridge', {
  feedApple: (details) => ipcRenderer.send('feed-apple', details),
  hideOverlay: () => ipcRenderer.send('hide-overlay'),
  onSpawnApple: (fn) => ipcRenderer.on('spawn-apple', (_, data) => fn(data)),
  onDropApple: (fn) => ipcRenderer.on('drop-apple', () => fn()),
});
