import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  // Window controls
  minimize: () => ipcRenderer.invoke('window:minimize'),
  maximize: () => ipcRenderer.invoke('window:maximize'),
  close: () => ipcRenderer.invoke('window:close'),
  isMaximized: () => ipcRenderer.invoke('window:isMaximized'),

  // Sidecar
  getBackendPort: () => ipcRenderer.invoke('sidecar:port'),
  isPackaged: () => ipcRenderer.invoke('sidecar:isPackaged'),

  // File dialog
  openFile: () => ipcRenderer.invoke('dialog:openFile'),

  // Persistent store (electron-store via main process)
  store: {
    get: (key: string) => ipcRenderer.invoke('store:get', key),
    set: (key: string, value: unknown) => ipcRenderer.invoke('store:set', key, value),
    delete: (key: string) => ipcRenderer.invoke('store:delete', key),
  },
})
