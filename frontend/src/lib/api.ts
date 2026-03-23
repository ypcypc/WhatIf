let BASE_URL = ''

export function setBaseUrl(url: string) {
  BASE_URL = url
}

// --- SSE Types ---

export type SSEEvent =
  | { type: 'chunk'; text: string }
  | { type: 'audio'; audio: string; index: number }
  | { type: 'state'; data: GameStateData }
  | { type: 'error'; message: string }
  | { type: 'done' }

export interface GameStateData {
  phase: 'setup' | 'confrontation' | 'resolution' | null
  eventId: string | null
  turn: number
  awaitingNextEvent?: boolean
  gameEnded?: boolean
  eventHasImage?: boolean
}

export interface GameState {
  phase: 'setup' | 'confrontation' | 'resolution' | null
  event: EventInfo | null
  turn: number
  playerName: string | null
  awaitingNextEvent: boolean
  gameEnded: boolean
}

export interface EventInfo {
  id: string
  decisionText: string
  goal: string
  importance: 'key' | 'normal' | 'optional'
  type: 'interactive' | 'narrative'
  hasImage?: boolean
}

export interface SaveInfo {
  slot: number
  saveTime: string
  playerName: string
  currentPhase: string | null
  currentEventId: string | null
  totalTurns: number
  description: string
  worldpkgTitle: string
}

export interface SaveGameResponse {
  message: string
}

export interface LoadGameResponse {
  text: string
  phase: 'setup' | 'confrontation' | 'resolution' | null
  eventId: string | null
  turn: number
}

// --- SSE Stream Reader ---

async function* readSSEStream(url: string, options: RequestInit): AsyncGenerator<SSEEvent> {
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  if (!res.body) throw new Error('No response body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ') && eventType) {
          const data = line.slice(6)
          try {
            const parsed = JSON.parse(data)
            if (eventType === 'chunk') yield { type: 'chunk', text: parsed.text }
            else if (eventType === 'audio') yield { type: 'audio', audio: parsed.audio, index: parsed.index }
            else if (eventType === 'state') yield { type: 'state', data: parsed }
            else if (eventType === 'error') yield { type: 'error', message: parsed.message }
            else if (eventType === 'done') yield { type: 'done' }
          } catch { /* skip malformed JSON */ }
          eventType = ''
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// --- Game API ---

export interface VoiceInfo {
  name: string
  gender: string
  friendlyName: string
}

function gameQuery(tts: boolean, voice?: string, lang?: string): string {
  const params = new URLSearchParams()
  if (tts) {
    params.set('tts', 'true')
    if (voice) params.set('voice', voice)
  }
  if (lang) params.set('lang', lang)
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export function startGame(tts = false, voice?: string, lang?: string) {
  return readSSEStream(`${BASE_URL}/api/game/start${gameQuery(tts, voice, lang)}`, { method: 'POST' })
}

export function submitAction(action: string, tts = false, voice?: string, lang?: string) {
  return readSSEStream(`${BASE_URL}/api/game/action${gameQuery(tts, voice, lang)}`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
}

export function continueGame(tts = false, voice?: string, lang?: string) {
  return readSSEStream(`${BASE_URL}/api/game/continue${gameQuery(tts, voice, lang)}`, { method: 'POST' })
}

export function getEventImageUrl(eventId: string): string {
  return `${BASE_URL}/api/game/event-image/${eventId}`
}

export async function getGameState(): Promise<GameState> {
  const res = await fetch(`${BASE_URL}/api/game/state`)
  return res.json()
}

export async function saveGame(slot: number, description: string) {
  const res = await fetch(`${BASE_URL}/api/game/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slot, description }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<SaveGameResponse>
}

export async function loadGame(slot: number): Promise<LoadGameResponse> {
  const res = await fetch(`${BASE_URL}/api/game/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ slot }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getSaves(): Promise<SaveInfo[]> {
  const res = await fetch(`${BASE_URL}/api/game/saves`)
  const data = await res.json()
  return data.saves ?? []
}

// --- Config API ---

export async function updateApiKeys(keys: Record<string, string>) {
  const res = await fetch(`${BASE_URL}/api/config/api-keys`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ keys }),
  })
  return res.json()
}

export async function testApiKey(provider: string, key: string) {
  const res = await fetch(`${BASE_URL}/api/config/test-key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, key }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail)
  }
  return res.json()
}

export async function getLlmConfig() {
  const res = await fetch(`${BASE_URL}/api/config/llm`)
  return res.json()
}

export async function updateLlmConfig(config: unknown) {
  const res = await fetch(`${BASE_URL}/api/config/llm`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return res.json()
}

// --- WorldPkg API ---

export interface WorldPkgInfo {
  name: string
  filename: string
  size: number
  hasCover?: boolean
}

export function getWorldPkgCoverUrl(filename: string): string {
  return `${BASE_URL}/api/config/worldpkg/cover/${filename}`
}

export async function getWorldPkgs(): Promise<{ packages: WorldPkgInfo[]; current: string | null }> {
  const res = await fetch(`${BASE_URL}/api/config/worldpkgs`)
  return res.json()
}

export async function loadWorldPkg(filename: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/config/worldpkg/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail)
  }
}

export async function importWorldPkg(file: File): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/api/config/worldpkg/import`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail)
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/api/health`)
    return res.ok
  } catch {
    return false
  }
}

// --- Voice API ---

export async function getVoices(): Promise<VoiceInfo[]> {
  const res = await fetch(`${BASE_URL}/api/voice/voices`)
  const data = await res.json()
  return data.voices ?? []
}

export async function segmentVoiceText(text: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/api/voice/segment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  const data = await res.json()
  return data.segmented ?? text
}
