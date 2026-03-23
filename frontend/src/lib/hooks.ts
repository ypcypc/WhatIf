import { useState, useEffect } from 'react'
import { setBaseUrl, checkHealth, updateApiKeys, updateLlmConfig } from './api'
import { getApiKeys, getLlmConfig, hasAnyApiKey } from './config-store'

export type AppReadyState = 'loading' | 'needs-config' | 'ready'

/**
 * Manages backend connection lifecycle:
 * 1. In Electron: get port from main process, wait for health check
 * 2. Sync stored API keys and LLM config to backend
 * 3. Check if API keys are configured
 */
export function useBackendReady(): AppReadyState {
  const [state, setState] = useState<AppReadyState>('loading')

  useEffect(() => {
    let cancelled = false

    async function init() {
      if (window.electronAPI) {
        const isPackaged = await window.electronAPI.isPackaged()
        if (isPackaged) {
          const port = await window.electronAPI.getBackendPort()
          setBaseUrl(`http://127.0.0.1:${port}`)
        } else {
          setBaseUrl('')
        }
      } else {
        setBaseUrl('')
      }

      for (let i = 0; i < 30; i++) {
        if (cancelled) return
        if (await checkHealth()) break
        await new Promise(r => setTimeout(r, 500))
      }

      if (cancelled) return

      const keys = await getApiKeys()
      if (Object.keys(keys).length > 0) {
        try { await updateApiKeys(keys) } catch { /* ignore */ }
      }

      const llmConfig = await getLlmConfig()
      if (llmConfig) {
        try { await updateLlmConfig(llmConfig) } catch { /* ignore */ }
      }

      if (cancelled) return
      const hasKeys = await hasAnyApiKey()
      setState(hasKeys ? 'ready' : 'needs-config')
    }

    init()
    return () => { cancelled = true }
  }, [])

  return state
}
