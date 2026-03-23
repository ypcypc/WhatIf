import { useState, useRef, useEffect } from 'react'
import { Send, X, Mic } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { segmentVoiceText } from '@/lib/api'

interface Props {
  onSubmit: (action: string) => void
  onCancel: () => void
  transcript?: string
  isListening?: boolean
  onToggleMic?: () => void
  micSupported?: boolean
}

export function ActionInput({ onSubmit, onCancel, transcript, isListening, onToggleMic, micSupported }: Props) {
  const [text, setText] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { t } = useTranslation()

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!transcript) return

    let cancelled = false
    const frameId = window.requestAnimationFrame(() => {
      if (cancelled) return
      setText(transcript)
      segmentVoiceText(transcript)
        .then(segmented => {
          if (!cancelled) {
            setText(prev => (prev === transcript ? segmented : prev))
          }
        })
        .catch(() => {})
    })

    return () => {
      cancelled = true
      window.cancelAnimationFrame(frameId)
    }
  }, [transcript])

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (text.trim()) onSubmit(text.trim())
    }
    if (e.key === 'Escape') onCancel()
  }

  return (
    <div className="mx-auto w-full max-w-2xl glass-card border-accent-gold/30 p-4">
      <motion.div
        animate={isFocused
          ? { boxShadow: '0 0 0 2px rgba(202, 138, 4, 0.3)' }
          : { boxShadow: '0 0 0 0px rgba(202, 138, 4, 0)' }
        }
        transition={{ duration: 0.2 }}
        className="rounded-lg"
      >
        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={t('gameplay.inputPlaceholder')}
          rows={3}
          className="w-full resize-none rounded-lg bg-bg-primary/50 px-4 py-3 font-sans text-text-primary placeholder-text-muted outline-none"
        />
      </motion.div>
      <div className="mt-3 flex justify-end gap-2">
        {micSupported && onToggleMic && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            animate={isListening
              ? { boxShadow: ['0 0 0 0 rgba(239,68,68,0.4)', '0 0 0 8px rgba(239,68,68,0)'] }
              : { boxShadow: '0 0 0 0 rgba(239,68,68,0)' }
            }
            transition={isListening ? { duration: 1.5, repeat: Infinity } : { duration: 0.2 }}
            onClick={onToggleMic}
            className={`cursor-pointer flex items-center gap-1 rounded-lg px-4 py-2 text-sm transition-colors duration-200 ${
              isListening
                ? 'bg-red-500/20 text-red-400'
                : 'text-text-muted hover:bg-bg-surface-hover hover:text-text-secondary'
            }`}
          >
            <Mic size={14} className={isListening ? 'animate-pulse' : ''} />
          </motion.button>
        )}
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={onCancel}
          className="cursor-pointer flex items-center gap-1 rounded-lg px-4 py-2 text-sm text-text-muted hover:bg-bg-surface-hover hover:text-text-secondary transition-colors duration-200"
        >
          <X size={14} />
          {t('gameplay.cancel')}
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => text.trim() && onSubmit(text.trim())}
          disabled={!text.trim()}
          className="cursor-pointer flex items-center gap-1 rounded-lg bg-accent-gold px-4 py-2 text-sm font-medium text-bg-primary hover:bg-accent-amber disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-200"
        >
          <Send size={14} />
          {t('gameplay.submit')}
        </motion.button>
      </div>
    </div>
  )
}
