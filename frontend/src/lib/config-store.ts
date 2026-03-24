// Persistent config store — uses electron-store via preload bridge,
// falls back to localStorage in browser dev mode.

export interface LlmSlotConfig {
  model: string
  temperature: number
  thinking_budget: number
  api_base?: string
  api_key_env?: string
}

export interface LlmConfigMap {
  extractors: Record<string, LlmSlotConfig>
  agents: Record<string, LlmSlotConfig>
}

const isElectron = () => typeof window !== 'undefined' && !!window.electronAPI

async function storeGet<T>(key: string): Promise<T | null> {
  if (isElectron()) {
    return (await window.electronAPI!.store.get(key)) as T | null
  }
  const raw = localStorage.getItem(key)
  return raw ? JSON.parse(raw) : null
}

async function storeSet(key: string, value: unknown): Promise<void> {
  if (isElectron()) {
    await window.electronAPI!.store.set(key, value)
  } else {
    localStorage.setItem(key, JSON.stringify(value))
  }
}

// --- API Keys ---

export async function getApiKeys(): Promise<Record<string, string>> {
  return (await storeGet<Record<string, string>>('api_keys')) ?? {}
}

export async function setApiKeys(keys: Record<string, string>): Promise<void> {
  const existing = await getApiKeys()
  await storeSet('api_keys', { ...existing, ...keys })
}

// --- LLM Config ---

export async function getLlmConfig(): Promise<LlmConfigMap | null> {
  return storeGet<LlmConfigMap>('llm_config')
}

export async function setLlmConfig(config: LlmConfigMap): Promise<void> {
  await storeSet('llm_config', config)
}

// --- Locale ---

export async function getLocale(): Promise<string> {
  return (await storeGet<string>('locale')) ?? 'zh-CN'
}

export async function setLocale(locale: string): Promise<void> {
  await storeSet('locale', locale)
}

// --- Voice Config ---

export interface VoiceConfig {
  enabled: boolean
  voice: string
}

const DEFAULT_VOICE_CONFIG: VoiceConfig = {
  enabled: false,
  voice: 'zh-CN-XiaoxiaoNeural',
}

export async function getVoiceConfig(): Promise<VoiceConfig> {
  return (await storeGet<VoiceConfig>('voice_config')) ?? DEFAULT_VOICE_CONFIG
}

export async function setVoiceConfig(config: VoiceConfig): Promise<void> {
  await storeSet('voice_config', config)
}

// --- Last selected WorldPkg ---

export interface LastPkg {
  filename: string
  name: string
}

export async function getLastPkg(): Promise<LastPkg | null> {
  return storeGet<LastPkg>('last_pkg')
}

export async function setLastPkg(filename: string, name: string): Promise<void> {
  await storeSet('last_pkg', { filename, name })
}

// --- Has any API key configured? ---

export async function hasAnyApiKey(): Promise<boolean> {
  const keys = await getApiKeys()
  return Object.values(keys).some(k => k.length > 0)
}
