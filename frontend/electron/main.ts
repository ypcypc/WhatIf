import { app, BrowserWindow, dialog, ipcMain } from 'electron'
import path from 'node:path'
import Store from 'electron-store'
import { startSidecar, stopSidecar, getSidecarPort } from './sidecar'

const store = new Store({ name: 'settings' })
let mainWindow: BrowserWindow | null = null

const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL

async function createWindow() {
  if (app.isPackaged) {
    await startSidecar()
  }

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    backgroundColor: '#0F0F23',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.once('ready-to-show', () => mainWindow?.show())

  if (VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }
}

// Window control IPC
ipcMain.handle('window:minimize', () => mainWindow?.minimize())
ipcMain.handle('window:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow?.maximize()
  }
})
ipcMain.handle('window:close', () => mainWindow?.close())
ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false)

// Sidecar IPC
ipcMain.handle('sidecar:port', () => getSidecarPort())
ipcMain.handle('sidecar:isPackaged', () => app.isPackaged)

// File dialog IPC
ipcMain.handle('dialog:openFile', async () => {
  if (!mainWindow) return null
  const result = await dialog.showOpenDialog(mainWindow, {
    filters: [{ name: 'WorldPkg', extensions: ['wpkg'] }],
    properties: ['openFile'],
  })
  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
})

// Store IPC
ipcMain.handle('store:get', (_e, key: string) => store.get(key))
ipcMain.handle('store:set', (_e, key: string, value: unknown) => store.set(key, value))
ipcMain.handle('store:delete', (_e, key: string) => store.delete(key))

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  stopSidecar()
  app.quit()
})
