import { useState, useRef, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'motion/react'
import { StoryViewport, type StoryEntry, type StoryViewportHandle } from '@/components/story-viewport'
import { SaveSlotsModal } from '@/components/save-slots-modal'
import { ActionInput } from '@/components/action-input'
import { CommandBar, type ConversationState } from '@/components/command-bar'
import { startGame, submitAction, continueGame, getEventImageUrl, segmentVoiceText, saveGame, getSaves, type SaveInfo, type SSEEvent, type GameStateData } from '@/lib/api'
import { audioPlayer } from '@/lib/audio-player'
import { useSpeechRecognition } from '@/lib/use-speech-recognition'
import { getVoiceConfig, setVoiceConfig, type VoiceConfig } from '@/lib/config-store'
import i18n from '@/lib/i18n'
import { ArrowDown, ArrowLeft, Eye, EyeOff } from 'lucide-react'

type Mode = 'READ' | 'INPUT' | 'GENERATING'

const TTS_TO_MIC_DELAY = 300  // ms delay after TTS before starting mic
const AUTO_CONTINUE_DELAY = 3000  // ms delay before auto-continue in non-confrontation

export interface GameplayResumeState {
  text: string
  phase: 'setup' | 'confrontation' | 'resolution' | null
  eventId: string | null
  turn: number
  awaitingNextEvent: boolean
  gameEnded: boolean
  eventHasImage: boolean
}

interface Props {
  onBack: () => void
  initialLoad?: GameplayResumeState | null
}

export function GameplayPage({ onBack, initialLoad = null }: Props) {
  const { t } = useTranslation()
  const [entries, setEntries] = useState<StoryEntry[]>([])
  const [mode, setMode] = useState<Mode>('GENERATING')
  const [phase, setPhase] = useState<string | null>(null)
  const [awaitingNextEvent, setAwaitingNextEvent] = useState(false)
  const [gameEnded, setGameEnded] = useState(false)
  const [showJumpBtn, setShowJumpBtn] = useState(false)
  const [debugMode, setDebugMode] = useState(false)
  const debugRef = useRef(false)
  const [bgImageUrl, setBgImageUrl] = useState<string | null>(null)
  const [textHidden, setTextHidden] = useState(false)
  const [showBackConfirm, setShowBackConfirm] = useState(false)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveSlots, setSaveSlots] = useState<SaveInfo[]>([])
  const [saveSlotsBusy, setSaveSlotsBusy] = useState(false)
  const [saveSlotsError, setSaveSlotsError] = useState<string | null>(null)
  const [saveToast, setSaveToast] = useState<string | null>(null)
  const viewportRef = useRef<StoryViewportHandle>(null)
  const entryIdRef = useRef(0)
  const startedRef = useRef(false)
  const prevEventIdRef = useRef<string | null>(null)
  const streamInFlightRef = useRef(false)
  const autoContinueTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)
  const startListeningTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)

  const [voiceConfig, setVoiceConfigState] = useState<VoiceConfig>({ enabled: false, voice: 'zh-CN-XiaoxiaoNeural' })
  const [voiceConfigReady, setVoiceConfigReady] = useState(false)
  const locale = i18n.language

  const [conversationMode, setConversationMode] = useState(false)
  const [convState, setConvState] = useState<ConversationState>('off')
  const conversationModeRef = useRef(false)
  const phaseRef = useRef<string | null>(null)
  const awaitingRef = useRef(false)

  useEffect(() => {
    conversationModeRef.current = conversationMode
    phaseRef.current = phase
    awaitingRef.current = awaitingNextEvent
    debugRef.current = debugMode
  }, [conversationMode, phase, awaitingNextEvent, debugMode])

  // Debug mode toggle: Ctrl+Shift+D (10x TTS speed + auto-continue)
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault()
        setDebugMode(prev => {
          const next = !prev
          audioPlayer.playbackRate = next ? 10 : 1
          return next
        })
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
  const doSubmitRef = useRef<(action: string) => void>(() => {})
  const continueRef = useRef<(origin?: 'manual' | 'auto') => void>(() => {})

  const clearScheduledAutoContinue = useCallback(() => {
    if (autoContinueTimeoutRef.current) {
      window.clearTimeout(autoContinueTimeoutRef.current)
      autoContinueTimeoutRef.current = null
    }
  }, [])

  const clearScheduledStartListening = useCallback(() => {
    if (startListeningTimeoutRef.current) {
      window.clearTimeout(startListeningTimeoutRef.current)
      startListeningTimeoutRef.current = null
    }
  }, [])

  const queueAutoContinue = useCallback((delay: number) => {
    clearScheduledAutoContinue()
    autoContinueTimeoutRef.current = window.setTimeout(() => {
      autoContinueTimeoutRef.current = null
      if (conversationModeRef.current || debugRef.current) {
        continueRef.current('auto')
      }
    }, delay)
  }, [clearScheduledAutoContinue])

  const revealLatestTurn = useCallback((behavior: ScrollBehavior = 'smooth') => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        viewportRef.current?.scrollToBottom(behavior)
      })
    })
  }, [])

  // Speech recognition with silence auto-submit (voice → segment → submit)
  const handleSilenceSubmit = useCallback(async (text: string) => {
    if (!conversationModeRef.current || streamInFlightRef.current) return
    try {
      const segmented = await segmentVoiceText(text)
      doSubmitRef.current(segmented)
    } catch {
      doSubmitRef.current(text)
    }
  }, [])

  const { transcript, isListening, startListening, stopListening, supported: micSupported } = useSpeechRecognition(
    locale === 'en' ? 'en-US' : 'zh-CN',
    handleSilenceSubmit,
  )

  const queueStartListening = useCallback((delay: number) => {
    clearScheduledStartListening()
    startListeningTimeoutRef.current = window.setTimeout(() => {
      startListeningTimeoutRef.current = null
      if (conversationModeRef.current) {
        startListening({ continuous: true })
      }
    }, delay)
  }, [clearScheduledStartListening, startListening])

  useEffect(() => {
    let cancelled = false

    getVoiceConfig()
      .then((config) => {
        if (!cancelled) {
          setVoiceConfigState(config)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setVoiceConfigReady(true)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  // Setup TTS completion → auto listen / auto continue
  useEffect(() => {
    audioPlayer.onComplete = () => {
      const isConv = conversationModeRef.current
      const isDebug = debugRef.current
      if (!isConv && !isDebug) return

      const p = phaseRef.current
      const awaiting = awaitingRef.current

      if (isConv && p === 'confrontation' && !awaiting) {
        setConvState('listening')
        queueStartListening(TTS_TO_MIC_DELAY)
      } else if (p === 'setup' || p === 'resolution' || awaiting) {
        if (isConv) setConvState('submitting')
        const delay = isDebug ? 200 : AUTO_CONTINUE_DELAY
        queueAutoContinue(delay)
      }
    }
    return () => { audioPlayer.onComplete = null }
  }, [queueAutoContinue, queueStartListening])

  useEffect(() => {
    return () => {
      clearScheduledAutoContinue()
      clearScheduledStartListening()
    }
  }, [clearScheduledAutoContinue, clearScheduledStartListening])

  const nextId = () => `entry-${++entryIdRef.current}`

  const preloadEventBackground = useCallback((eventId: string | null, eventHasImage: boolean) => {
    if (!eventId || !eventHasImage) {
      setBgImageUrl(null)
      return
    }

    const url = getEventImageUrl(eventId)
    const img = new Image()
    img.onload = () => setBgImageUrl(url)
    img.onerror = () => setBgImageUrl(null)
    img.src = url
  }, [])

  const createResumeEntries = useCallback((text: string) => {
    const blocks = text
      .split(/\n\s*\n/)
      .map(block => block.trim())
      .filter(Boolean)

    if (blocks.length === 0) {
      return [{ id: nextId(), kind: 'system' as const, status: 'final' as const, text: t('saves.resumeFallback') }]
    }

    return blocks.map((block) => ({
      id: nextId(),
      kind: block.startsWith('> ') ? 'player' as const : 'narration' as const,
      status: 'final' as const,
      text: block.startsWith('> ') ? block.replace(/^>\s*/, '') : block,
    }))
  }, [t])

  const processStream = useCallback(async (
    stream: AsyncGenerator<SSEEvent>,
    options?: { revealLatest?: boolean; scrollBehavior?: ScrollBehavior },
  ) => {
    const revealLatest = options?.revealLatest ?? false
    const scrollBehavior = options?.scrollBehavior ?? 'smooth'
    streamInFlightRef.current = true
    setMode('GENERATING')
    if (conversationModeRef.current) setConvState('speaking')
    const streamId = nextId()
    let streamInserted = false
    let streamHasText = false

    const ensureStreamEntry = () => {
      if (streamInserted) return
      streamInserted = true
      setEntries(prev => [...prev, { id: streamId, kind: 'narration', status: 'streaming', text: '' }])
      if (revealLatest) {
        revealLatestTurn(scrollBehavior)
      }
    }

    const ttsEnabled = conversationModeRef.current || voiceConfig.enabled
    if (ttsEnabled) {
      audioPlayer.reset()
      audioPlayer.unlock()
    }

    try {
      for await (const event of stream) {
        if (event.type === 'chunk') {
          ensureStreamEntry()
          streamHasText = true
          setEntries(prev =>
            prev.map(e =>
              e.id === streamId ? { ...e, text: e.text + event.text } : e,
            ),
          )
        } else if (event.type === 'audio') {
          audioPlayer.enqueue(event.audio)
        } else if (event.type === 'state') {
          const s = event.data as GameStateData
          setPhase(s.phase)
          setAwaitingNextEvent(s.awaitingNextEvent ?? false)
          setGameEnded(s.gameEnded ?? false)
          if (s.gameEnded && conversationModeRef.current) {
            clearScheduledAutoContinue()
            clearScheduledStartListening()
            stopListening()
            setConversationMode(false)
            setConvState('off')
          }
          if (s.eventId && s.eventId !== prevEventIdRef.current) {
            if (prevEventIdRef.current) {
              const dividerText = t('gameplay.newEventDivider')
              setEntries(prev => {
                const last = prev[prev.length - 1]
                if (last?.kind === 'system' && last.text === dividerText) {
                  return prev
                }
                return [...prev, { id: nextId(), kind: 'system', status: 'final', text: dividerText }]
              })
            }
            preloadEventBackground(s.eventId, s.eventHasImage ?? false)
          }
          prevEventIdRef.current = s.eventId ?? null
        } else if (event.type === 'error') {
          if (!streamInserted) {
            streamInserted = true
            setEntries(prev => [...prev, { id: streamId, kind: 'narration', status: 'error', text: event.message }])
            if (revealLatest) {
              revealLatestTurn(scrollBehavior)
            }
          } else if (!streamHasText) {
            setEntries(prev =>
              prev.map(e => (e.id === streamId ? { ...e, status: 'error', text: event.message } : e)),
            )
          }
        }
      }

      if (streamInserted && streamHasText) {
        setEntries(prev =>
          prev.map(e => (e.id === streamId && e.status !== 'error' ? { ...e, status: 'final' } : e)),
        )
      }
      setMode('READ')

      if (!audioPlayer.isPlaying && (conversationModeRef.current || debugRef.current)) {
        audioPlayer.onComplete?.()
      }
    } finally {
      streamInFlightRef.current = false
    }
  }, [clearScheduledAutoContinue, clearScheduledStartListening, preloadEventBackground, revealLatestTurn, stopListening, t, voiceConfig.enabled])

  const doSubmitAction = useCallback((action: string) => {
    if (streamInFlightRef.current) return
    clearScheduledAutoContinue()
    clearScheduledStartListening()
    if (isListening) stopListening()
    audioPlayer.stop()
    setConvState(conversationModeRef.current ? 'submitting' : 'off')
    setEntries(prev => [...prev, { id: nextId(), kind: 'player', status: 'final', text: action }])
    const tts = conversationModeRef.current || voiceConfig.enabled
    void processStream(submitAction(action, tts, voiceConfig.voice, locale), {
      revealLatest: true,
      scrollBehavior: conversationModeRef.current ? 'auto' : 'smooth',
    })
  }, [clearScheduledAutoContinue, clearScheduledStartListening, isListening, locale, processStream, stopListening, voiceConfig.enabled, voiceConfig.voice])

  function handleTakeTurn() {
    audioPlayer.stop()
    setMode('INPUT')
  }

  const handleContinue = useCallback((origin: 'manual' | 'auto' = 'manual') => {
    if (streamInFlightRef.current) return
    clearScheduledAutoContinue()
    clearScheduledStartListening()
    audioPlayer.stop()
    if (conversationModeRef.current && origin === 'auto') {
      setConvState('submitting')
    }
    const tts = conversationModeRef.current || voiceConfig.enabled || debugRef.current
    void processStream(continueGame(tts, voiceConfig.voice, locale), {
      revealLatest: true,
      scrollBehavior: conversationModeRef.current ? 'auto' : 'smooth',
    })
  }, [clearScheduledAutoContinue, clearScheduledStartListening, locale, processStream, voiceConfig.enabled, voiceConfig.voice])

  const refreshSaveSlots = useCallback(async () => {
    const saves = await getSaves()
    setSaveSlots(saves)
  }, [])

  const openSaveModal = useCallback(async () => {
    setShowSaveModal(true)
    setSaveSlotsError(null)
    setSaveSlotsBusy(true)
    try {
      await refreshSaveSlots()
    } catch (error) {
      setSaveSlotsError(error instanceof Error ? error.message : t('saves.saveFailed'))
    } finally {
      setSaveSlotsBusy(false)
    }
  }, [refreshSaveSlots, t])

  const handleSaveSlot = useCallback(async (slot: number, description: string) => {
    setSaveSlotsError(null)
    setSaveSlotsBusy(true)
    try {
      const result = await saveGame(slot, description)
      await refreshSaveSlots()
      setSaveToast(result.message)
      setShowSaveModal(false)
    } catch (error) {
      setSaveSlotsError(error instanceof Error ? error.message : t('saves.saveFailed'))
    } finally {
      setSaveSlotsBusy(false)
    }
  }, [refreshSaveSlots, t])

  const requestBackToHome = useCallback(() => {
    setShowBackConfirm(true)
  }, [])

  const cancelBackToHome = useCallback(() => {
    setShowBackConfirm(false)
  }, [])

  const handleBackToHome = useCallback(() => {
    clearScheduledAutoContinue()
    clearScheduledStartListening()
    stopListening()
    audioPlayer.stop()
    setConversationMode(false)
    setConvState('off')
    setShowBackConfirm(false)
    setShowSaveModal(false)
    onBack()
  }, [clearScheduledAutoContinue, clearScheduledStartListening, onBack, stopListening])

  useEffect(() => {
    if (!showBackConfirm) return

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        setShowBackConfirm(false)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [showBackConfirm])

  useEffect(() => {
    if (!saveToast) return

    const timeoutId = window.setTimeout(() => setSaveToast(null), 2600)
    return () => window.clearTimeout(timeoutId)
  }, [saveToast])

  function handleToggleConversation() {
    const next = !conversationMode
    setConversationMode(next)
    if (next) {
      if (!voiceConfig.enabled) {
        const nextVoice = { ...voiceConfig, enabled: true }
        setVoiceConfigState(nextVoice)
        setVoiceConfig(nextVoice)
      }
      if (mode === 'READ') {
        const needsContinue = phase === 'setup' || phase === 'resolution' || awaitingNextEvent
        if (needsContinue) {
          setConvState('submitting')
          queueAutoContinue(300)
        } else if (phase === 'confrontation' && !awaitingNextEvent) {
          setConvState('listening')
          queueStartListening(TTS_TO_MIC_DELAY)
        }
      }
    } else {
      clearScheduledAutoContinue()
      clearScheduledStartListening()
      stopListening()
      audioPlayer.stop()
      setConvState('off')
      const restored = { ...voiceConfig, enabled: false }
      setVoiceConfigState(restored)
      setVoiceConfig(restored)
    }
  }

  useEffect(() => {
    doSubmitRef.current = doSubmitAction
    continueRef.current = handleContinue
  }, [doSubmitAction, handleContinue])

  useEffect(() => {
    if (!voiceConfigReady || startedRef.current) return

    let cancelled = false
    const timeoutId = window.setTimeout(() => {
      if (cancelled || startedRef.current) return
      startedRef.current = true

      if (initialLoad) {
        const restoredEntries = createResumeEntries(initialLoad.text)
        setEntries(restoredEntries)
        setMode('READ')
        setPhase(initialLoad.phase)
        setAwaitingNextEvent(initialLoad.awaitingNextEvent)
        setGameEnded(initialLoad.gameEnded)
        prevEventIdRef.current = initialLoad.eventId
        preloadEventBackground(initialLoad.eventId, initialLoad.eventHasImage)
        revealLatestTurn('auto')
        return
      }

      const tts = conversationModeRef.current || voiceConfig.enabled
      void processStream(startGame(tts, voiceConfig.voice, locale))
    }, 0)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [createResumeEntries, initialLoad, locale, preloadEventBackground, processStream, revealLatestTurn, voiceConfig.enabled, voiceConfig.voice, voiceConfigReady])

  return (
    <div className="relative flex h-full flex-col pt-8" style={{ zIndex: 10 }}>
      <button
        onClick={requestBackToHome}
        className="fixed top-12 left-4 z-30 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs cursor-pointer transition-all duration-200"
        style={{
          background: 'rgba(0,0,0,0.4)',
          backdropFilter: 'blur(8px)',
          color: 'rgba(255,255,255,0.76)',
          border: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        <ArrowLeft size={14} />
        {t('gameplay.backToHome')}
      </button>

      {/* Debug mode indicator */}
      {debugMode && (
        <div
          className="fixed top-2 right-4 z-50 flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-mono"
          style={{
            background: 'rgba(220,50,50,0.15)',
            border: '1px solid rgba(220,50,50,0.4)',
            color: '#f08080',
            backdropFilter: 'blur(8px)',
          }}
        >
          <span className="inline-block h-2 w-2 rounded-full animate-pulse" style={{ background: '#f08080' }} />
          DEBUG: 10x Speed
          <button
            onClick={() => { setDebugMode(false); audioPlayer.playbackRate = 1 }}
            className="ml-2 cursor-pointer opacity-60 hover:opacity-100"
            style={{ color: '#f08080' }}
          >
            &times;
          </button>
        </div>
      )}

      <AnimatePresence>
        {saveToast && (
          <motion.div
            key={saveToast}
            initial={{ opacity: 0, y: 10, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="fixed top-12 left-1/2 z-40 -translate-x-1/2 rounded-full px-4 py-2 text-sm"
            style={{
              background: 'rgba(12,21,40,0.9)',
              border: '1px solid rgba(232,160,32,0.18)',
              color: 'var(--color-text-0)',
              boxShadow: '0 16px 36px rgba(0,0,0,0.32), 0 0 24px rgba(232,160,32,0.08)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
            }}
          >
            {saveToast}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showBackConfirm && (
          <>
            <motion.button
              key="back-confirm-overlay"
              type="button"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={cancelBackToHome}
              className="fixed inset-0 z-40 cursor-pointer"
              style={{
                background: 'radial-gradient(circle at 50% 42%, rgba(232,160,32,0.08) 0%, rgba(4,8,15,0.72) 42%, rgba(4,8,15,0.88) 100%)',
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
              }}
            />
            <motion.div
              key="back-confirm-dialog"
              initial={{ opacity: 0, y: 18, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
              className="fixed inset-x-4 top-1/2 z-50 mx-auto w-full max-w-md -translate-y-1/2 rounded-2xl px-6 py-5"
              style={{
                background: 'linear-gradient(180deg, rgba(12,21,40,0.94) 0%, rgba(7,14,28,0.96) 100%)',
                border: '1px solid rgba(232,160,32,0.18)',
                boxShadow: '0 24px 80px rgba(0,0,0,0.48), 0 0 0 1px rgba(255,255,255,0.03), 0 0 42px rgba(232,160,32,0.08)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
              }}
            >
              <div
                className="mb-4 h-px w-full"
                style={{
                  background: 'linear-gradient(90deg, transparent 0%, rgba(232,160,32,0.18) 20%, rgba(232,160,32,0.7) 50%, rgba(232,160,32,0.18) 80%, transparent 100%)',
                }}
              />
              <div className="space-y-2">
                <p
                  className="text-[11px] font-sans uppercase tracking-[0.28em]"
                  style={{ color: 'var(--color-accent-gold)' }}
                >
                  {t('gameplay.backConfirmEyebrow')}
                </p>
                <h2
                  className="font-serif text-[22px] leading-tight"
                  style={{ color: 'var(--color-text-0)' }}
                >
                  {t('gameplay.backConfirmTitle')}
                </h2>
                <p
                  className="font-sans text-sm leading-6"
                  style={{ color: 'var(--color-text-1)' }}
                >
                  {t('gameplay.backConfirmBody')}
                </p>
                <p
                  className="font-sans text-xs leading-5"
                  style={{ color: 'rgba(232,160,32,0.82)' }}
                >
                  {t('gameplay.backConfirmHint')}
                </p>
              </div>

              <div className="mt-6 flex items-center justify-end gap-3">
                <button
                  onClick={cancelBackToHome}
                  className="cursor-pointer rounded-lg px-4 py-2.5 text-sm transition-colors duration-200"
                  style={{
                    border: '0.5px solid var(--color-border)',
                    color: 'var(--color-text-1)',
                    background: 'rgba(255,255,255,0.02)',
                  }}
                >
                  {t('gameplay.backConfirmStay')}
                </button>
                <button
                  onClick={handleBackToHome}
                  className="cursor-pointer rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200"
                  style={{
                    background: 'linear-gradient(135deg, rgba(232,160,32,0.94) 0%, rgba(196,112,16,0.92) 100%)',
                    color: '#1c0e00',
                    boxShadow: '0 8px 24px rgba(232,160,32,0.24)',
                  }}
                >
                  {t('gameplay.backConfirmLeave')}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <SaveSlotsModal
        open={showSaveModal}
        mode="save"
        saves={saveSlots}
        busy={saveSlotsBusy}
        error={saveSlotsError}
        onClose={() => {
          if (!saveSlotsBusy) {
            setShowSaveModal(false)
            setSaveSlotsError(null)
          }
        }}
        onSave={handleSaveSlot}
      />

      {/* Galgame-style background image (always mounted, opacity-controlled) */}
      <div
        className="fixed inset-0 z-0 transition-opacity duration-700"
        style={{ opacity: bgImageUrl ? 1 : 0, pointerEvents: 'none' }}
      >
        {bgImageUrl && (
          <img
            src={bgImageUrl}
            className="h-full w-full object-cover"
            alt=""
          />
        )}
        {/* Gradient overlay for text readability — fades with textHidden */}
        <div
          className="absolute inset-0 transition-opacity duration-300"
          style={{
            opacity: textHidden ? 0 : 1,
            background: 'linear-gradient(180deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.7) 40%, rgba(0,0,0,0.9) 100%)',
          }}
        />
      </div>

      {/* Toggle text visibility button (only when background image exists) */}
      {bgImageUrl && (
        <button
          onClick={() => setTextHidden(prev => !prev)}
          className="fixed top-12 right-4 z-30 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs cursor-pointer transition-all duration-200"
          style={{
            background: 'rgba(0,0,0,0.4)',
            backdropFilter: 'blur(8px)',
            color: 'rgba(255,255,255,0.7)',
            border: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          {textHidden ? <Eye size={14} /> : <EyeOff size={14} />}
          {textHidden ? t('gameplay.showText', '显示文本') : t('gameplay.hideText', '隐藏文本')}
        </button>
      )}

      {/* Story area — flex-1 preserved, opacity-controlled for text hide */}
      <StoryViewport
        ref={viewportRef}
        entries={entries}
        onScrollAwayChange={setShowJumpBtn}
        textHidden={textHidden}
      />

      {/* Jump to bottom */}
      <AnimatePresence>
        {showJumpBtn && (
          <motion.button
            key="jump-btn"
            initial={{ opacity: 0, y: 10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 5, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            onClick={() => viewportRef.current?.scrollToBottom()}
            className="cursor-pointer fixed bottom-20 right-6 z-20 flex items-center gap-1 rounded-full glass-card px-3 py-1.5 text-xs transition-colors duration-200"
            style={{ color: 'var(--color-text-1)' }}
          >
            <ArrowDown size={12} />
            {t('gameplay.jumpToLatest')}
          </motion.button>
        )}
      </AnimatePresence>

      {/* Action input (text mode only, hidden in conversation mode) */}
      <AnimatePresence>
        {mode === 'INPUT' && !conversationMode && (
          <motion.div
            key="action-input"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="relative z-10 px-4 pb-2"
          >
            <ActionInput
              onSubmit={doSubmitAction}
              onCancel={() => setMode('READ')}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Command bar */}
      <AnimatePresence>
        {!gameEnded && (
          <motion.div
            key="command-bar"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3 }}
            className="relative z-10"
          >
            <CommandBar
              phase={phase}
              generating={mode === 'GENERATING'}
              awaitingNextEvent={awaitingNextEvent}
              onTakeTurn={handleTakeTurn}
              onContinue={handleContinue}
              onSave={openSaveModal}
              conversationMode={conversationMode}
              conversationState={convState}
              onToggleConversation={handleToggleConversation}
              liveTranscript={transcript}
              micSupported={micSupported}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
