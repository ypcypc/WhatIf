import { type KeyboardEvent, useEffect, useRef, useState } from 'react'

import { ActionComposer } from '@/components/gameplay/action-composer'
import { BackgroundLayer } from '@/components/gameplay/background-layer'
import { CommandBar } from '@/components/gameplay/command-bar'
import { StorySkeleton } from '@/components/gameplay/story-skeleton'
import { StoryViewport, type StoryViewportHandle } from '@/components/gameplay/story-viewport'
import { TopBar } from '@/components/gameplay/top-bar'
import * as api from '@/lib/api'
import type { SSEStatePayload, StoryEntry, StoryMode } from '@/types/gameplay'

let entryCounter = 0
function nextId() {
  return `e${++entryCounter}`
}

const noop = () => {}

export function GameplayPage() {
  const [storyEntries, setStoryEntries] = useState<StoryEntry[]>([])
  const [mode, setMode] = useState<StoryMode>('READ')
  const [draft, setDraft] = useState('')
  const [phase, setPhase] = useState<string | null>(null)
  const [awaitingNextEvent, setAwaitingNextEvent] = useState(false)
  const [gameEnded, setGameEnded] = useState(false)
  const [showJumpToLatest, setShowJumpToLatest] = useState(false)
  const startedRef = useRef(false)
  const viewportRef = useRef<StoryViewportHandle>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const pendingRequestRef = useRef<number | null>(null)
  const requestCounterRef = useRef(0)
  const nearBottomRef = useRef(true)
  const prevEntryCountRef = useRef(0)

  function pushEntry(kind: StoryEntry['kind'], text: string, status: StoryEntry['status'] = 'final') {
    const id = nextId()
    setStoryEntries((prev) => [...prev, { id, kind, status, text }])
    return id
  }

  function patchEntry(
    id: string,
    updater: (entry: StoryEntry) => StoryEntry,
  ) {
    setStoryEntries((prev) => prev.map((entry) => (entry.id === id ? updater(entry) : entry)))
  }

  function beginGeneration() {
    const requestId = ++requestCounterRef.current
    pendingRequestRef.current = requestId
    const placeholderId = nextId()
    setStoryEntries((prev) => [
      ...prev,
      { id: placeholderId, kind: 'narration', status: 'streaming', text: '' },
    ])
    setMode('GENERATING')
    return { requestId, placeholderId }
  }

  function isActiveRequest(requestId: number) {
    return pendingRequestRef.current === requestId
  }

  function finishGeneration(requestId: number) {
    if (!isActiveRequest(requestId)) return
    pendingRequestRef.current = null
    setMode('READ')
  }

  function appendError(message: string, placeholderId?: string) {
    setStoryEntries((prev) => {
      let entries = prev
      if (placeholderId) {
        entries = prev.filter((entry) => !(entry.id === placeholderId && !entry.text.trim()))
      }
      return [
        ...entries,
        { id: nextId(), kind: 'system', status: 'error', text: `Error: ${message}` },
      ]
    })
  }

  async function syncState() {
    const state = await api.getGameState()
    setPhase(state.phase)
    setAwaitingNextEvent(state.awaitingNextEvent)
    setGameEnded(state.gameEnded)
  }

  function onStateEvent(state: SSEStatePayload) {
    setPhase(state.phase)
    if (state.awaitingNextEvent !== undefined) {
      setAwaitingNextEvent(state.awaitingNextEvent)
    }
    if (state.gameEnded !== undefined) {
      setGameEnded(state.gameEnded)
    }
  }

  function handleNearBottomChange(isNearBottom: boolean) {
    nearBottomRef.current = isNearBottom
    if (isNearBottom) {
      setShowJumpToLatest(false)
    }
  }

  function handleJumpToLatest() {
    viewportRef.current?.scrollToBottom('smooth')
    setShowJumpToLatest(false)
  }

  useEffect(() => {
    if (mode !== 'INPUT') return
    composerRef.current?.focus()
  }, [mode])

  useEffect(() => {
    if (!storyEntries.length) return
    const isNewEntry = storyEntries.length > prevEntryCountRef.current
    prevEntryCountRef.current = storyEntries.length

    if (isNewEntry && nearBottomRef.current) {
      // 新条目添加时滚动到该条目起始位置（仅一次）
      const lastEntry = storyEntries[storyEntries.length - 1]
      requestAnimationFrame(() => {
        viewportRef.current?.scrollToEntry(lastEntry.id)
      })
      return
    }

    // 流式更新或用户已滚离底部 → 不自动滚动，显示"跳到最新"按钮
    if (!nearBottomRef.current && isNewEntry) {
      setShowJumpToLatest(true)
    }
  }, [storyEntries])

  async function runStreamingAction(action: string, addPlayerEntry: boolean) {
    const trimmed = action.trim()
    if (!trimmed || mode === 'GENERATING') return

    if (addPlayerEntry) {
      pushEntry('player', trimmed, 'final')
    }

    const { requestId, placeholderId } = beginGeneration()

    try {
      await api.submitAction(
        trimmed,
        (chunk) => {
          if (!isActiveRequest(requestId)) return
          patchEntry(placeholderId, (entry) => ({
            ...entry,
            text: entry.text + chunk,
          }))
        },
        () => {
          if (!isActiveRequest(requestId)) return
          patchEntry(placeholderId, (entry) => ({ ...entry, status: 'final' }))
        },
        (state) => {
          if (!isActiveRequest(requestId)) return
          onStateEvent(state)
        },
      )

      if (!isActiveRequest(requestId)) return
      patchEntry(placeholderId, (entry) => ({ ...entry, status: 'final' }))
      await syncState()
    } catch (error) {
      if (!isActiveRequest(requestId)) return
      appendError(error instanceof Error ? error.message : String(error), placeholderId)
    } finally {
      finishGeneration(requestId)
    }
  }

  async function runContinueNarrative() {
    if (mode === 'GENERATING') return
    const { requestId, placeholderId } = beginGeneration()

    try {
      await api.continueGame(
        (chunk) => {
          if (!isActiveRequest(requestId)) return
          patchEntry(placeholderId, (entry) => ({
            ...entry,
            text: entry.text + chunk,
          }))
        },
        () => {
          if (!isActiveRequest(requestId)) return
          patchEntry(placeholderId, (entry) => ({ ...entry, status: 'final' }))
        },
        (state) => {
          if (!isActiveRequest(requestId)) return
          onStateEvent(state)
        },
      )

      if (!isActiveRequest(requestId)) return
      patchEntry(placeholderId, (entry) => ({ ...entry, status: 'final' }))
      await syncState()
    } catch (error) {
      if (!isActiveRequest(requestId)) return
      appendError(error instanceof Error ? error.message : String(error), placeholderId)
    } finally {
      finishGeneration(requestId)
    }
  }

  // 开始游戏
  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    async function init() {
      const { requestId, placeholderId } = beginGeneration()

      try {
        await api.startGame(
          (chunk) => {
            if (!isActiveRequest(requestId)) return
            patchEntry(placeholderId, (entry) => ({
              ...entry,
              text: entry.text + chunk,
            }))
          },
          () => {
            if (!isActiveRequest(requestId)) return
            patchEntry(placeholderId, (entry) => ({ ...entry, status: 'final' }))
          },
          (state) => {
            if (!isActiveRequest(requestId)) return
            onStateEvent(state)
          },
        )

        if (!isActiveRequest(requestId)) return
        patchEntry(placeholderId, (entry) => ({ ...entry, status: 'final' }))
        await syncState()
      } catch (error) {
        if (!isActiveRequest(requestId)) return
        appendError(error instanceof Error ? error.message : String(error), placeholderId)
      } finally {
        finishGeneration(requestId)
      }
    }
    void init()
  }, [])

  // TAKE A TURN
  function handleTakeATurn() {
    if (mode !== 'READ') return
    if (phase !== 'confrontation' || awaitingNextEvent || gameEnded) return
    setDraft('')
    setMode('INPUT')
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== 'Enter') return
    if (event.ctrlKey) return
    if (event.shiftKey || event.altKey || event.metaKey) return
    event.preventDefault()
    void handleSubmitAction()
  }

  async function handleSubmitAction() {
    if (!draft.trim()) return
    const actionText = draft.trim()
    setDraft('')
    await runStreamingAction(actionText, true)
  }

  function handleCancelComposer() {
    setDraft('')
    setMode('READ')
  }

  function canUseContinueEndpoint() {
    return phase === 'setup' || phase === 'resolution' || awaitingNextEvent
  }

  // CONTINUE
  async function handleContinue() {
    if (mode !== 'READ') return
    if (gameEnded) return
    if (canUseContinueEndpoint()) {
      await runContinueNarrative()
      return
    }
    await runStreamingAction('CONTINUE', false)
  }

  return (
    <main className="gameplay-shell">
      <BackgroundLayer />
      <div className="surface gameplay-surface-shell">
        <div className="surface-content">
          <TopBar
            title="WhatIf"
            onGameMenu={noop}
            onModelSwitcher={noop}
            onUndo={noop}
            onRedo={noop}
            onSettings={noop}
          />
          <StoryViewport
            ref={viewportRef}
            storyEntries={storyEntries}
            showJumpToLatest={showJumpToLatest}
            onJumpToLatest={handleJumpToLatest}
            onNearBottomChange={handleNearBottomChange}
            emptySlot={mode === 'GENERATING' ? <StorySkeleton /> : undefined}
          />
          {mode === 'READ' && (
            <CommandBar
              onTakeATurn={handleTakeATurn}
              onContinue={() => void handleContinue()}
              onRetry={noop}
              onErase={noop}
              takeATurnDisabled={phase !== 'confrontation' || awaitingNextEvent || gameEnded}
              continueDisabled={phase === null || gameEnded}
              retryDisabled
              eraseDisabled
              retryTitle="即将推出"
              eraseTitle="即将推出"
            />
          )}
          {mode === 'GENERATING' && (
            <div className="surface-card generating-bar rounded-full">
              <div className="generating-shimmer" />
              <span>正在生成</span>
              <span className="generating-dots" aria-hidden>
                <i />
                <i />
                <i />
              </span>
            </div>
          )}
        </div>
      </div>

      {mode === 'INPUT' && (
        <ActionComposer
          value={draft}
          onChange={setDraft}
          onCancel={handleCancelComposer}
          onSubmit={() => void handleSubmitAction()}
          onKeyDown={handleComposerKeyDown}
          textareaRef={composerRef}
        />
      )}
    </main>
  )
}
