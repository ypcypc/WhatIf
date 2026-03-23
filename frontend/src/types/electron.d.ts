interface ElectronStore {
  get: (key: string) => Promise<unknown>
  set: (key: string, value: unknown) => Promise<void>
  delete: (key: string) => Promise<void>
}

interface ElectronAPI {
  minimize: () => Promise<void>
  maximize: () => Promise<void>
  close: () => Promise<void>
  isMaximized: () => Promise<boolean>
  getBackendPort: () => Promise<number>
  isPackaged: () => Promise<boolean>
  openFile: () => Promise<string | null>
  store: ElectronStore
}

interface Window {
  electronAPI?: ElectronAPI
}
