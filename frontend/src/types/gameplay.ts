export type ActivePanel = 'none' | 'menu' | 'settings' | 'modelSwitcher'
export type StoryMode = 'READ' | 'INPUT' | 'GENERATING'

export interface StoryEntry {
  id: string
  kind: 'narration' | 'player' | 'system'
  status: 'final' | 'streaming' | 'error'
  text: string
}

export interface GameplayViewState {
  mode: StoryMode
  activePanel: ActivePanel
  storyEntries: StoryEntry[]
}

export interface GameplayHandlers {
  openGameMenu(): void
  openModelSwitcher(): void
  undo(): void
  redo(): void
  openSettings(): void
  takeATurn(): void
  continueStory(): void
  retry(): void
  erase(): void
  submitAction(text: string): void
  cancelComposer(): void
}

// ===== API 响应类型（对应 backend/api/schemas.py）=====

export interface EventInfo {
  id: string
  decisionText: string
  goal: string
  importance: 'key' | 'normal' | 'optional'
  type: 'interactive' | 'narrative'
}

export interface GameState {
  phase: 'setup' | 'confrontation' | 'resolution' | null
  event: EventInfo | null
  turn: number
  playerName: string | null
  awaitingNextEvent: boolean
  gameEnded: boolean
}

export interface NarrativeResponse {
  text: string
  phase: string | null
  eventId: string | null
  turn: number
}

export interface SSEChunkPayload {
  text: string
}

export interface SSEStatePayload {
  phase: string | null
  eventId: string | null
  turn: number
  awaitingNextEvent?: boolean
  gameEnded?: boolean
}

export interface SaveInfo {
  slot: number
  saveTime: string
  playerName: string
  currentEventId: string | null
  currentPhase: string | null
  totalTurns: number
  description: string
  worldpkgTitle: string
}
