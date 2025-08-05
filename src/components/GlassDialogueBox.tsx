import { type FC, useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, RotateCcw, ArrowRight, User } from 'lucide-react'

interface GlassDialogueBoxProps {
  characterName?: string
  dialogueText?: string
  isWaitingForInput?: boolean
  isProcessing?: boolean
  defaultReply?: string
  onSubmit?: (input: string) => void
  showContinueHint?: boolean
}

export const GlassDialogueBox: FC<GlassDialogueBoxProps> = ({
  characterName = '系统',
  dialogueText = '游戏正在加载...',
  isWaitingForInput = false,
  isProcessing = false,
  defaultReply = '',
  onSubmit,
  showContinueHint = false
}) => {
  const [inputValue, setInputValue] = useState('')
  const [showInput, setShowInput] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-focus input when it appears
  useEffect(() => {
    if (showInput && inputRef.current) {
      inputRef.current.focus()
    }
  }, [showInput])

  // Handle input mode
  useEffect(() => {
    if (isWaitingForInput) {
      setShowInput(true)
      setInputValue(defaultReply)
    } else {
      setShowInput(false)
      setInputValue('')
    }
  }, [isWaitingForInput, defaultReply])

  const handleSubmit = () => {
    if (inputValue.trim() && onSubmit) {
      onSubmit(inputValue.trim())
      setInputValue('')
      setShowInput(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // No continue handler needed - handled by parent component

  return (
    <div className="fixed inset-x-0 bottom-0 h-1/3 pointer-events-none">
      <motion.div
        initial={{ opacity: 0, y: 100 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 200, damping: 25 }}
        className="pointer-events-auto w-full h-full p-4"
      >
        <div className="w-full h-full bg-black/60 backdrop-blur-xl border border-white/20 rounded-t-3xl shadow-2xl overflow-hidden">
          <div className="w-full h-full flex flex-col">
            {/* Character Name Bar */}
            <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10 bg-white/5">
              <User size={16} className="text-white/70" />
              <span className="text-white font-medium">{characterName}</span>
            </div>

            {/* Dialogue Content */}
            <div className="flex-1 p-6 overflow-y-auto">
              <motion.div
                key={dialogueText}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="text-white/90 text-lg leading-relaxed mb-4 break-words overflow-wrap-anywhere max-w-full"
              >
                {dialogueText}
              </motion.div>

              {/* Status Indicators */}
              <div className="flex items-center gap-4 mb-4">
                {isProcessing && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center gap-2 text-blue-400 text-sm"
                  >
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      className="w-4 h-4 border-2 border-current border-t-transparent rounded-full"
                    />
                    AI 正在思考...
                  </motion.div>
                )}

                {showContinueHint && !isProcessing && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center gap-2 text-white/60 text-sm"
                  >
                    <motion.div
                      animate={{ opacity: [1, 0.5, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    >
                      点击继续或按 Enter
                    </motion.div>
                    <ArrowRight size={16} />
                  </motion.div>
                )}
              </div>
            </div>

            {/* Input Area */}
            <AnimatePresence>
              {showInput && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  className="border-t border-white/10 px-6 py-4"
                >
                  <div className="flex gap-3 items-end">
                    <div className="flex-1">
                      <textarea
                        ref={inputRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="输入你的回复..."
                        disabled={isProcessing}
                        className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3
                                  text-white placeholder-white/50 resize-none min-h-[80px]
                                  focus:outline-none focus:ring-2 focus:ring-white/30
                                  backdrop-blur-sm transition-all duration-200
                                  disabled:opacity-50 disabled:cursor-not-allowed"
                        rows={2}
                      />
                      {defaultReply && (
                        <div className="mt-2 text-xs text-white/60">
                          推荐回复: {defaultReply}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-2">
                      <button
                        onClick={handleSubmit}
                        disabled={!inputValue.trim() || isProcessing}
                        title="发送 (Enter)"
                        className="px-4 py-2 bg-white/20 hover:bg-white/30 disabled:bg-white/10 disabled:text-gray-500 rounded-xl transition-colors font-medium text-white backdrop-blur-sm border border-white/20"
                      >
                        <Send size={16} />
                      </button>
                      {defaultReply && (
                        <button
                          onClick={() => setInputValue(defaultReply)}
                          title="使用推荐回复"
                          className="px-3 py-1.5 bg-transparent hover:bg-white/10 border border-transparent rounded-xl transition-colors text-white/80 hover:text-white backdrop-blur-sm"
                        >
                          <RotateCcw size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

          </div>
        </div>
      </motion.div>
    </div>
  )
}