import { spawn, type ChildProcess } from 'node:child_process'
import path from 'node:path'

let sidecarProcess: ChildProcess | null = null
let backendPort = 0

export async function startSidecar(): Promise<void> {
  const exe = path.join(
    process.resourcesPath,
    'sidecar',
    'whatif-server',
    process.platform === 'win32' ? 'whatif-server.exe' : 'whatif-server',
  )

  return new Promise((resolve, reject) => {
    sidecarProcess = spawn(exe, [], {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: path.dirname(exe),
      windowsHide: true,
    })

    const timeout = setTimeout(() => reject(new Error('Sidecar startup timeout')), 30_000)

    sidecarProcess.stdout?.on('data', (data: Buffer) => {
      const match = data.toString().match(/__PORT__:(\d+)/)
      if (match) {
        backendPort = parseInt(match[1])
        pollHealth(backendPort)
          .then(() => { clearTimeout(timeout); resolve() })
          .catch(reject)
      }
    })

    sidecarProcess.stderr?.on('data', (data: Buffer) => {
      console.error('[sidecar stderr]', data.toString())
    })

    sidecarProcess.on('error', (err) => {
      clearTimeout(timeout)
      reject(err)
    })

    sidecarProcess.on('exit', (code) => {
      if (code !== null && code !== 0) {
        clearTimeout(timeout)
        reject(new Error(`Sidecar exited with code ${code}`))
      }
    })
  })
}

async function pollHealth(port: number, retries = 30): Promise<void> {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/health`)
      if (res.ok) return
    } catch { /* server not ready yet */ }
    await new Promise(r => setTimeout(r, 500))
  }
  throw new Error('Backend health check failed after 15s')
}

export function getSidecarPort(): number {
  return backendPort
}

export function stopSidecar(): void {
  if (sidecarProcess) {
    sidecarProcess.kill()
    sidecarProcess = null
  }
}
