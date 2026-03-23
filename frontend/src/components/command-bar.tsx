import { Sword, FastForward, Save, MessageSquare, MessageSquareOff, Mic } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { AnimatePresence, motion } from 'motion/react'

export type ConversationState = 'off' | 'speaking' | 'listening' | 'submitting'

interface Props {
  phase: string | null
  generating: boolean
  awaitingNextEvent: boolean
  onTakeTurn: () => void
  onContinue: () => void
  onSave: () => void
  conversationMode: boolean
  conversationState: ConversationState
  onToggleConversation: () => void
  liveTranscript: string
  micSupported: boolean
}

export function CommandBar({
  phase, generating, awaitingNextEvent,
  onTakeTurn, onContinue, onSave,
  conversationMode, conversationState, onToggleConversation,
  liveTranscript, micSupported,
}: Props) {
  const { t } = useTranslation()
  const canTakeTurn = phase === 'confrontation' && !generating && !awaitingNextEvent
  const canContinue = !generating && (phase === 'setup' || phase === 'resolution' || awaitingNextEvent)
  const hasMainAction = canTakeTurn || canContinue || generating

  return (
    <div
      className="flex items-center gap-3 px-4 py-3"
      style={{
        background: 'rgba(7,14,28,0.6)',
        borderTop: '0.5px solid var(--color-border)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
    >
      {/* Conversation mode toggle */}
      {micSupported && (
        <button
          onClick={onToggleConversation}
          className="cursor-pointer flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-all duration-200"
          style={{
            background: conversationMode ? 'var(--color-amber-dim)' : 'transparent',
            border: `0.5px solid ${conversationMode ? 'var(--color-amber-border)' : 'var(--color-border)'}`,
            color: conversationMode ? 'var(--color-accent-gold)' : 'var(--color-text-1)',
          }}
          title={conversationMode ? t('gameplay.conversationOn') : t('gameplay.conversationOff')}
        >
          {conversationMode ? <MessageSquare size={16} /> : <MessageSquareOff size={16} />}
        </button>
      )}

      {/* Conversation mode: live transcript subtitle */}
      {conversationMode && conversationState === 'listening' && (
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Mic size={14} className="animate-pulse flex-shrink-0" style={{ color: 'var(--color-accent-gold)' }} />
          <span
            className="text-sm font-sans truncate"
            style={{ color: liveTranscript ? 'var(--color-text-0)' : 'var(--color-text-2)' }}
          >
            {liveTranscript || t('gameplay.listening')}
          </span>
        </div>
      )}

      {conversationMode && conversationState === 'speaking' && (
        <div className="flex items-center gap-2 flex-1">
          {/* Sound wave animation */}
          <span className="flex items-center gap-[3px]">
            {[0, 1, 2, 3, 4].map(i => (
              <motion.span
                key={i}
                className="w-[3px] rounded-full"
                style={{ background: 'var(--color-accent-gold)' }}
                animate={{ height: ['8px', '16px', '8px'] }}
                transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.12, ease: 'easeInOut' }}
              />
            ))}
          </span>
          <span className="text-sm font-sans" style={{ color: 'var(--color-text-1)' }}>
            {t('gameplay.speaking')}
          </span>
        </div>
      )}

      {conversationMode && conversationState === 'submitting' && (
        <div className="flex items-center gap-2 flex-1">
          <span className="flex gap-1">
            {[0, 1, 2].map(i => (
              <motion.span
                key={i}
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: 'var(--color-accent-gold)' }}
                animate={{ opacity: [0.35, 1, 0.35] }}
                transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.18 }}
              />
            ))}
          </span>
          <span className="text-sm font-sans" style={{ color: 'var(--color-text-1)' }}>
            {t('gameplay.autoContinuing')}
          </span>
        </div>
      )}

      {/* Standard mode buttons */}
      <AnimatePresence mode="popLayout">
        {/* Take Turn: hidden in conversation mode (voice input replaces it) */}
        {!conversationMode && canTakeTurn && (
          <motion.button
            key="take-turn"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            onClick={onTakeTurn}
            className="cursor-pointer flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors duration-200"
            style={{
              background: 'var(--color-accent-gold)',
              color: 'var(--color-bg-primary)',
            }}
          >
            <Sword size={16} />
            {t('gameplay.takeTurn')}
          </motion.button>
        )}

        {/* Continue: always visible when available (manual fallback for conversation mode) */}
        {canContinue && conversationState !== 'speaking' && conversationState !== 'submitting' && (
          <motion.button
            key="continue"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            onClick={onContinue}
            className="cursor-pointer flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm transition-colors duration-200"
            style={{
              border: '0.5px solid var(--color-amber-border)',
              color: 'var(--color-accent-gold)',
            }}
          >
            <FastForward size={16} />
            {t('gameplay.continue')}
          </motion.button>
        )}

        {generating && (
          <motion.span
            key="generating"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 text-sm"
            style={{ color: 'var(--color-text-1)' }}
          >
            <span className="flex gap-0.5">
              {[0, 1, 2].map(i => (
                <motion.span
                  key={i}
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: 'var(--color-accent-gold)' }}
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </span>
            {t('gameplay.generating')}
          </motion.span>
        )}
      </AnimatePresence>

      <button
        onClick={onSave}
        disabled={generating}
        className={`cursor-pointer flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm transition-colors duration-200 disabled:opacity-40 disabled:cursor-not-allowed ${hasMainAction || conversationMode ? 'ml-auto' : ''}`}
        style={{
          color: 'var(--color-text-1)',
          border: '0.5px solid var(--color-border)',
        }}
      >
        <Save size={16} />
        {t('gameplay.save')}
      </button>
    </div>
  )
}
