import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'

export interface StoryEntry {
  id: string
  kind: 'narration' | 'player' | 'system'
  status: 'final' | 'streaming' | 'error'
  text: string
}

export interface StoryViewportHandle {
  scrollToBottom: (behavior?: ScrollBehavior) => void
  isNearBottom: () => boolean
}

interface Props {
  entries: StoryEntry[]
  onScrollAwayChange?: (away: boolean) => void
  textHidden?: boolean
}

const entryEase: [number, number, number, number] = [0.16, 1, 0.3, 1]

export const StoryViewport = forwardRef<StoryViewportHandle, Props>(({ entries, onScrollAwayChange, textHidden = false }, ref) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const isNearBottom = useCallback(() => {
    const el = containerRef.current
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < 120
  }, [])

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    bottomRef.current?.scrollIntoView({ behavior })
  }, [])

  useImperativeHandle(ref, () => ({ scrollToBottom, isNearBottom }))

  // Auto-scroll only when a new entry appears (not on every streaming chunk)
  const entryCount = entries.length
  const prevCountRef = useRef(0)
  useEffect(() => {
    if (entryCount > prevCountRef.current && isNearBottom()) {
      scrollToBottom()
    }
    prevCountRef.current = entryCount
  }, [entryCount, scrollToBottom, isNearBottom])

  const handleScroll = useCallback(() => {
    onScrollAwayChange?.(!isNearBottom())
  }, [isNearBottom, onScrollAwayChange])

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="relative z-10 flex-1 overflow-y-auto px-4 pt-12 pb-4 transition-opacity duration-300"
      style={{ opacity: textHidden ? 0 : 1, pointerEvents: textHidden ? 'none' : 'auto' }}
    >
      <div className="mx-auto max-w-2xl">
        {entries.map((entry) => (
          <StoryEntryBlock key={entry.id} entry={entry} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
})

StoryViewport.displayName = 'StoryViewport'

function StoryEntryBlock({ entry }: { entry: StoryEntry }) {
  const { t } = useTranslation()

  if (entry.kind === 'player') {
    return (
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.35, ease: entryEase }}
        className="mb-6 glass-card border-accent-gold/20 px-4 py-3"
      >
        <p className="font-sans text-sm text-accent-amber leading-relaxed">
          {entry.text}
        </p>
      </motion.div>
    )
  }

  if (entry.kind === 'system') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, ease: entryEase }}
        className="my-8"
      >
        <div className="flex items-center gap-4">
          <div
            className="h-px flex-1"
            style={{ background: 'linear-gradient(90deg, transparent 0%, rgba(232,160,32,0.2) 100%)' }}
          />
          <span
            className="rounded-full px-3 py-1 text-[10px] font-sans tracking-[0.18em] uppercase"
            style={{
              color: 'var(--color-accent-gold)',
              background: 'rgba(232,160,32,0.08)',
              border: '1px solid rgba(232,160,32,0.18)',
              boxShadow: '0 0 20px rgba(232,160,32,0.08)',
            }}
          >
            {entry.text}
          </span>
          <div
            className="h-px flex-1"
            style={{ background: 'linear-gradient(90deg, rgba(232,160,32,0.2) 0%, transparent 100%)' }}
          />
        </div>
      </motion.div>
    )
  }

  if (entry.status === 'error') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, ease: entryEase }}
        className="mb-6 glass-card border-red-500/30 bg-red-500/5 px-5 py-4"
      >
        <p className="font-sans text-sm font-medium text-red-400 mb-1">
          {entry.text.includes('AuthenticationError') || entry.text.includes('API key')
            ? t('errors.invalidApiKey')
            : entry.text.includes('Connection') || entry.text.includes('timeout')
              ? t('errors.connectionFailed')
              : t('errors.generationError')}
        </p>
        <details className="mt-2">
          <summary className="text-xs text-text-muted cursor-pointer hover:text-text-secondary">
            {t('errors.viewDetails')}
          </summary>
          <pre className="mt-2 text-xs text-text-muted/80 whitespace-pre-wrap break-all font-sans">
            {entry.text}
          </pre>
        </details>
      </motion.div>
    )
  }

  const paragraphs = entry.text.split('\n').filter(p => p.trim())
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: entryEase }}
      className="mb-6"
    >
      {paragraphs.map((p, i) => (
        <p
          key={i}
          className="font-serif text-lg leading-[1.8] text-text-primary mb-4 last:mb-0"
        >
          {p}
          {entry.status === 'streaming' && i === paragraphs.length - 1 && (
            <motion.span
              className="inline-block ml-0.5 w-[2px] h-[1em] bg-accent-gold align-middle"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
            />
          )}
        </p>
      ))}
    </motion.div>
  )
}
