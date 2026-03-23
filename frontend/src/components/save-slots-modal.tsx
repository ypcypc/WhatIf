import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { ArchiveRestore, Bookmark, Clock3, FileClock, Save } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { SaveInfo } from '@/lib/api'
import i18n from '@/lib/i18n'

type Mode = 'save' | 'load'

interface Props {
  open: boolean
  mode: Mode
  saves: SaveInfo[]
  currentPkg?: string | null
  busy?: boolean
  error?: string | null
  onClose: () => void
  onSave?: (slot: number, description: string) => void | Promise<void>
  onLoad?: (save: SaveInfo) => void | Promise<void>
}

const MANUAL_SLOTS = [1, 2, 3, 4, 5, 6] as const

function formatSaveTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(i18n.language === 'zh-CN' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function phaseLabel(phase: string | null, t: ReturnType<typeof useTranslation>['t']) {
  switch (phase) {
    case 'setup':
      return t('saves.phaseSetup')
    case 'confrontation':
      return t('saves.phaseConfrontation')
    case 'resolution':
      return t('saves.phaseResolution')
    default:
      return t('saves.phaseUnknown')
  }
}

export function SaveSlotsModal({
  open,
  mode,
  saves,
  currentPkg,
  busy = false,
  error,
  onClose,
  onSave,
  onLoad,
}: Props) {
  const { t } = useTranslation()
  const [selectedSlotOverride, setSelectedSlotOverride] = useState<number | null>(null)
  const [descriptionDraft, setDescriptionDraft] = useState<string | null>(null)

  const savesBySlot = useMemo(
    () => new Map(saves.map((save) => [save.slot, save])),
    [saves],
  )

  const loadableSaves = useMemo(
    () => [...saves].sort((a, b) => b.saveTime.localeCompare(a.saveTime)),
    [saves],
  )

  const defaultSelectedSlot = mode === 'save'
    ? (MANUAL_SLOTS.find((slot) => !savesBySlot.has(slot)) ?? MANUAL_SLOTS[0])
    : (loadableSaves[0]?.slot ?? null)

  const selectedSlot = mode === 'load' && selectedSlotOverride !== null && !savesBySlot.has(selectedSlotOverride)
    ? defaultSelectedSlot
    : (selectedSlotOverride ?? defaultSelectedSlot)

  const defaultDescription = mode === 'save' && selectedSlot !== null
    ? (savesBySlot.get(selectedSlot)?.description ?? '')
    : ''

  const description = descriptionDraft ?? defaultDescription

  const selectedSave = selectedSlot !== null ? savesBySlot.get(selectedSlot) ?? null : null

  const resetLocalState = useCallback(() => {
    setSelectedSlotOverride(null)
    setDescriptionDraft(null)
  }, [])

  const handleClose = useCallback(() => {
    if (busy) return
    resetLocalState()
    onClose()
  }, [busy, onClose, resetLocalState])

  useEffect(() => {
    if (!open || busy) return

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        handleClose()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [busy, handleClose, open])

  const handleConfirm = async () => {
    if (mode === 'save') {
      if (selectedSlot === null || !onSave) return
      resetLocalState()
      await onSave(selectedSlot, description.trim())
      return
    }

    if (!selectedSave || !onLoad) return
    resetLocalState()
    await onLoad(selectedSave)
  }

  const title = mode === 'save' ? t('saves.saveTitle') : t('saves.loadTitle')
  const eyebrow = mode === 'save' ? t('saves.saveEyebrow') : t('saves.loadEyebrow')
  const subtitle = mode === 'save' ? t('saves.saveSubtitle') : t('saves.loadSubtitle')

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={handleClose}
            className="fixed inset-0 z-40 cursor-pointer"
            style={{
              background: 'radial-gradient(circle at 50% 42%, rgba(232,160,32,0.07) 0%, rgba(4,8,15,0.74) 42%, rgba(4,8,15,0.9) 100%)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
            }}
          />

          <motion.div
            initial={{ opacity: 0, y: 22, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            className="fixed inset-x-4 top-1/2 z-50 mx-auto flex max-h-[78vh] w-full max-w-3xl -translate-y-1/2 flex-col overflow-hidden rounded-3xl"
            style={{
              background: 'linear-gradient(180deg, rgba(12,21,40,0.95) 0%, rgba(7,14,28,0.97) 100%)',
              border: '1px solid rgba(232,160,32,0.18)',
              boxShadow: '0 30px 90px rgba(0,0,0,0.52), 0 0 0 1px rgba(255,255,255,0.03), 0 0 48px rgba(232,160,32,0.08)',
              backdropFilter: 'blur(22px)',
              WebkitBackdropFilter: 'blur(22px)',
            }}
          >
            <div className="px-6 pt-6 pb-5">
              <div
                className="mb-4 h-px w-full"
                style={{
                  background: 'linear-gradient(90deg, transparent 0%, rgba(232,160,32,0.18) 20%, rgba(232,160,32,0.7) 50%, rgba(232,160,32,0.18) 80%, transparent 100%)',
                }}
              />
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2">
                  <p
                    className="text-[11px] font-sans uppercase tracking-[0.28em]"
                    style={{ color: 'var(--color-accent-gold)' }}
                  >
                    {eyebrow}
                  </p>
                  <h2
                    className="font-serif text-[26px] leading-tight"
                    style={{ color: 'var(--color-text-0)' }}
                  >
                    {title}
                  </h2>
                  <p
                    className="max-w-2xl font-sans text-sm leading-6"
                    style={{ color: 'var(--color-text-1)' }}
                  >
                    {subtitle}
                  </p>
                </div>
                <button
                  onClick={handleClose}
                  disabled={busy}
                  className="cursor-pointer rounded-full px-3 py-1 text-xs transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
                  style={{
                    border: '0.5px solid var(--color-border)',
                    color: 'var(--color-text-1)',
                  }}
                >
                  {t('common.close')}
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-4">
              {mode === 'save' ? (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    {MANUAL_SLOTS.map((slot) => {
                      const save = savesBySlot.get(slot)
                      const selected = selectedSlot === slot
                      return (
                        <button
                          key={slot}
                          type="button"
                          onClick={() => {
                            setSelectedSlotOverride(slot)
                            setDescriptionDraft(savesBySlot.get(slot)?.description ?? '')
                          }}
                          className="cursor-pointer rounded-2xl p-4 text-left transition-all duration-200"
                          style={{
                            background: selected ? 'rgba(232,160,32,0.08)' : 'rgba(255,255,255,0.02)',
                            border: selected ? '1px solid rgba(232,160,32,0.34)' : '1px solid rgba(255,255,255,0.06)',
                            boxShadow: selected ? '0 0 0 1px rgba(232,160,32,0.12), 0 16px 36px rgba(0,0,0,0.24)' : 'none',
                          }}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <p className="font-sans text-xs uppercase tracking-[0.22em]" style={{ color: 'var(--color-accent-gold)' }}>
                                {t('saves.slotLabel', { slot })}
                              </p>
                              <p className="mt-1 font-serif text-lg" style={{ color: 'var(--color-text-0)' }}>
                                {save ? save.description : t('saves.emptySlot')}
                              </p>
                            </div>
                            <Save size={18} style={{ color: selected ? 'var(--color-accent-gold)' : 'var(--color-text-2)' }} />
                          </div>
                          <div className="mt-3 space-y-1 text-xs" style={{ color: 'var(--color-text-1)' }}>
                            <p>{save ? t('saves.saveTime', { time: formatSaveTime(save.saveTime) }) : t('saves.slotEmptyHint')}</p>
                            <p>
                              {save
                                ? `${phaseLabel(save.currentPhase, t)} · ${t('saves.turnInfo', { turn: save.totalTurns })}`
                                : t('saves.overwriteReady')}
                            </p>
                          </div>
                        </button>
                      )
                    })}
                  </div>

                  <div
                    className="rounded-2xl px-4 py-4"
                    style={{
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <Bookmark size={15} style={{ color: 'var(--color-accent-gold)' }} />
                      <span className="font-sans text-sm" style={{ color: 'var(--color-text-0)' }}>
                        {t('saves.descriptionLabel')}
                      </span>
                    </div>
                    <textarea
                      value={description}
                      onChange={(event) => setDescriptionDraft(event.target.value)}
                      rows={3}
                      className="w-full resize-none rounded-xl px-4 py-3 font-sans text-sm outline-none transition-colors"
                      style={{
                        background: 'rgba(7,14,28,0.8)',
                        border: '0.5px solid var(--color-border)',
                        color: 'var(--color-text-0)',
                      }}
                      placeholder={t('saves.descriptionPlaceholder')}
                    />
                    <p className="mt-2 text-xs" style={{ color: 'var(--color-text-2)' }}>
                      {t('saves.descriptionHint')}
                    </p>
                  </div>
                </div>
              ) : loadableSaves.length > 0 ? (
                <div className="space-y-3">
                  {loadableSaves.map((save) => {
                    const selected = selectedSlot === save.slot
                    const needsSwitch = currentPkg !== save.worldpkgTitle
                    return (
                      <button
                        key={save.slot}
                        type="button"
                        onClick={() => setSelectedSlotOverride(save.slot)}
                        className="cursor-pointer w-full rounded-2xl p-4 text-left transition-all duration-200"
                        style={{
                          background: selected ? 'rgba(232,160,32,0.08)' : 'rgba(255,255,255,0.02)',
                          border: selected ? '1px solid rgba(232,160,32,0.34)' : '1px solid rgba(255,255,255,0.06)',
                          boxShadow: selected ? '0 0 0 1px rgba(232,160,32,0.12), 0 16px 36px rgba(0,0,0,0.24)' : 'none',
                        }}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className="rounded-full px-2.5 py-1 text-[10px] font-sans uppercase tracking-[0.18em]"
                                style={{
                                  color: 'var(--color-accent-gold)',
                                  background: 'rgba(232,160,32,0.08)',
                                  border: '1px solid rgba(232,160,32,0.16)',
                                }}
                              >
                                {save.slot === 0 ? t('saves.autoSaveBadge') : t('saves.slotLabel', { slot: save.slot })}
                              </span>
                              <span className="text-xs" style={{ color: 'var(--color-text-2)' }}>
                                {save.worldpkgTitle}
                              </span>
                            </div>
                            <p className="mt-2 truncate font-serif text-xl" style={{ color: 'var(--color-text-0)' }}>
                              {save.description}
                            </p>
                            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs" style={{ color: 'var(--color-text-1)' }}>
                              <span className="flex items-center gap-1.5">
                                <Clock3 size={12} />
                                {t('saves.saveTime', { time: formatSaveTime(save.saveTime) })}
                              </span>
                              <span>{phaseLabel(save.currentPhase, t)}</span>
                              <span>{t('saves.turnInfo', { turn: save.totalTurns })}</span>
                            </div>
                            {needsSwitch && (
                              <p className="mt-3 text-xs" style={{ color: 'rgba(232,160,32,0.82)' }}>
                                {t('saves.packageSwitch', { name: save.worldpkgTitle })}
                              </p>
                            )}
                          </div>
                          <ArchiveRestore size={18} style={{ color: selected ? 'var(--color-accent-gold)' : 'var(--color-text-2)' }} />
                        </div>
                      </button>
                    )
                  })}
                </div>
              ) : (
                <div
                  className="flex min-h-[260px] flex-col items-center justify-center rounded-3xl border px-6 py-12 text-center"
                  style={{
                    borderColor: 'rgba(255,255,255,0.06)',
                    background: 'rgba(255,255,255,0.02)',
                  }}
                >
                  <FileClock size={30} style={{ color: 'var(--color-text-2)' }} />
                  <p className="mt-4 font-serif text-2xl" style={{ color: 'var(--color-text-0)' }}>
                    {t('saves.emptyTitle')}
                  </p>
                  <p className="mt-2 max-w-md text-sm leading-6" style={{ color: 'var(--color-text-1)' }}>
                    {t('saves.emptyBody')}
                  </p>
                </div>
              )}
            </div>

            <div className="border-t px-6 py-4" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="min-h-[20px] text-sm" style={{ color: error ? '#f08080' : 'var(--color-text-2)' }}>
                  {error ?? (mode === 'save' ? t('saves.saveHint') : t('saves.loadHint'))}
                </div>
                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={handleClose}
                    disabled={busy}
                    className="cursor-pointer rounded-lg px-4 py-2.5 text-sm transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40"
                    style={{
                      border: '0.5px solid var(--color-border)',
                      color: 'var(--color-text-1)',
                      background: 'rgba(255,255,255,0.02)',
                    }}
                  >
                    {t('common.cancel')}
                  </button>
                  <button
                    onClick={() => void handleConfirm()}
                    disabled={busy || selectedSlot === null || (mode === 'load' && loadableSaves.length === 0)}
                    className="cursor-pointer rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50"
                    style={{
                      background: 'linear-gradient(135deg, rgba(232,160,32,0.94) 0%, rgba(196,112,16,0.92) 100%)',
                      color: '#1c0e00',
                      boxShadow: '0 8px 24px rgba(232,160,32,0.24)',
                    }}
                  >
                    {busy
                      ? t('saves.processing')
                      : mode === 'save'
                        ? t('saves.saveNow')
                        : t('saves.loadNow')}
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
