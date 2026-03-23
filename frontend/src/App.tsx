import { useState, useRef, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'motion/react'
import { Titlebar } from '@/components/titlebar'
import { BackgroundLayers } from '@/components/background-layers'
import { LoadingScreen } from '@/components/loading-screen'
import { SaveSlotsModal } from '@/components/save-slots-modal'
import { StartPage } from '@/pages/start-page'
import { GameplayPage, type GameplayResumeState } from '@/pages/gameplay-page'
import { SettingsPage } from '@/pages/settings-page'
import { LibraryPage } from '@/pages/library-page'
import { useBackendReady } from '@/lib/hooks'
import { hasAnyApiKey, getLastPkg, setLastPkg } from '@/lib/config-store'
import { getWorldPkgs, loadWorldPkg, getSaves, loadGame, getGameState, type SaveInfo } from '@/lib/api'
import type { WhiteHoleHandle } from '@/components/particle-canvas'

type Page = 'start' | 'gameplay' | 'settings' | 'library'

const pageTransition = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -24 },
  transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] as const },
}

export default function App() {
  const { t } = useTranslation()
  const readyState = useBackendReady()
  const [page, setPage] = useState<Page>('start')
  const [currentPkg, setCurrentPkg] = useState<string | null>(null)
  const whiteHoleRef = useRef<WhiteHoleHandle>(null)
  const [keyOverride, setKeyOverride] = useState<boolean | null>(null)
  const [showLoadSaveModal, setShowLoadSaveModal] = useState(false)
  const [loadableSaves, setLoadableSaves] = useState<SaveInfo[]>([])
  const [loadSaveBusy, setLoadSaveBusy] = useState(false)
  const [loadSaveError, setLoadSaveError] = useState<string | null>(null)
  const [resumeState, setResumeState] = useState<GameplayResumeState | null>(null)

  const needsApiKey = keyOverride !== null ? !keyOverride : readyState === 'needs-config'

  useEffect(() => {
    if (readyState === 'loading') return
    let cancelled = false

    getLastPkg().then(async (last) => {
      if (!last || cancelled) return
      try {
        const data = await getWorldPkgs()
        if (cancelled) return

        if (data.current === last.name) {
          setCurrentPkg(last.name)
          return
        }

        await loadWorldPkg(last.filename)
        if (!cancelled) {
          setCurrentPkg(last.name)
        }
      } catch { /* package may have been deleted */ }
    })

    return () => {
      cancelled = true
    }
  }, [readyState])

  const handleSettingsBack = useCallback(async () => {
    const hasKeys = await hasAnyApiKey()
    setKeyOverride(hasKeys)
    setPage('start')
  }, [])

  const refreshSaves = useCallback(async () => {
    const saves = await getSaves()
    setLoadableSaves(saves)
  }, [])

  const openLoadSaveModal = useCallback(async () => {
    setShowLoadSaveModal(true)
    setLoadSaveError(null)
    setLoadSaveBusy(true)
    try {
      await refreshSaves()
    } catch (error) {
      setLoadSaveError(error instanceof Error ? error.message : t('saves.loadFailed'))
    } finally {
      setLoadSaveBusy(false)
    }
  }, [refreshSaves, t])

  const handleLoadSave = useCallback(async (save: SaveInfo) => {
    setLoadSaveError(null)
    setLoadSaveBusy(true)

    try {
      const pkgData = await getWorldPkgs()
      if (pkgData.current !== save.worldpkgTitle) {
        const match = pkgData.packages.find((pkg) => pkg.name === save.worldpkgTitle)
        if (!match) {
          throw new Error(t('saves.packageMissing', { name: save.worldpkgTitle }))
        }
        await loadWorldPkg(match.filename)
        setCurrentPkg(match.name)
        setLastPkg(match.filename, match.name)
      } else if (pkgData.current) {
        setCurrentPkg(pkgData.current)
      }

      const loaded = await loadGame(save.slot)
      if (loaded.text.startsWith('[错误]')) {
        throw new Error(loaded.text.replace(/^\[错误\]\s*/, ''))
      }

      const state = await getGameState()
      setResumeState({
        text: loaded.text,
        phase: loaded.phase,
        eventId: loaded.eventId ?? state.event?.id ?? null,
        turn: loaded.turn,
        awaitingNextEvent: state.awaitingNextEvent,
        gameEnded: state.gameEnded,
        eventHasImage: Boolean(state.event?.hasImage),
      })
      setShowLoadSaveModal(false)
      setPage('gameplay')
    } catch (error) {
      setLoadSaveError(error instanceof Error ? error.message : t('saves.loadFailed'))
    } finally {
      setLoadSaveBusy(false)
    }
  }, [t])

  function renderPage() {
    switch (page) {
      case 'start':
        return (
          <motion.div key="start" {...pageTransition} className="h-screen">
            <StartPage
              currentPkg={currentPkg}
              needsApiKey={needsApiKey}
              onStartGame={() => {
                setResumeState(null)
                setPage('gameplay')
              }}
              onSelectPkg={() => setPage('library')}
              onLoadSave={openLoadSaveModal}
              onSettings={() => setPage('settings')}
              whiteHoleRef={whiteHoleRef}
            />
          </motion.div>
        )
      case 'library':
        return (
          <motion.div key="library" {...pageTransition} className="h-screen">
            <LibraryPage
              currentPkg={currentPkg}
              onSelect={(filename, name) => {
                setCurrentPkg(name)
                setLastPkg(filename, name)
                setPage('start')
              }}
              onBack={() => setPage('start')}
            />
          </motion.div>
        )
      case 'gameplay':
        return (
          <motion.div key="gameplay" {...pageTransition} className="h-screen">
            <GameplayPage
              initialLoad={resumeState}
              onBack={() => setPage('start')}
            />
          </motion.div>
        )
      case 'settings':
        return (
          <motion.div key="settings" {...pageTransition} className="h-screen">
            <SettingsPage onBack={handleSettingsBack} />
          </motion.div>
        )
    }
  }

  return (
    <>
      <BackgroundLayers whiteHoleRef={whiteHoleRef} />
      <Titlebar />
      <SaveSlotsModal
        open={showLoadSaveModal}
        mode="load"
        saves={loadableSaves}
        currentPkg={currentPkg}
        busy={loadSaveBusy}
        error={loadSaveError}
        onClose={() => {
          if (!loadSaveBusy) {
            setShowLoadSaveModal(false)
            setLoadSaveError(null)
          }
        }}
        onLoad={handleLoadSave}
      />
      <AnimatePresence mode="wait">
        {readyState === 'loading' ? (
          <motion.div
            key="loading"
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.4 }}
          >
            <LoadingScreen />
          </motion.div>
        ) : (
          renderPage()
        )}
      </AnimatePresence>
    </>
  )
}
