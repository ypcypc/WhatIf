import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Minus, Square, X, Copy } from 'lucide-react'
import { motion } from 'motion/react'

export function Titlebar() {
  const { t } = useTranslation()
  const [maximized, setMaximized] = useState(false)
  const api = window.electronAPI

  useEffect(() => {
    if (!api) return
    api.isMaximized().then(setMaximized)
  }, [api])

  if (!api) return null

  return (
    <div className="titlebar-drag fixed top-0 left-0 right-0 z-50 flex h-8 items-center justify-between bg-gradient-to-r from-bg-primary/90 via-bg-primary/80 to-bg-primary/90 backdrop-blur-[12px] px-3">
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="text-xs text-text-muted font-sans select-none"
      >
        {t('app.name')}
      </motion.span>
      <div className="titlebar-no-drag flex items-center gap-1">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => api.minimize()}
          className="cursor-pointer rounded p-1 text-text-muted hover:bg-bg-surface hover:text-text-secondary transition-colors duration-200"
        >
          <Minus size={14} />
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={async () => {
            await api.maximize()
            setMaximized(await api.isMaximized())
          }}
          className="cursor-pointer rounded p-1 text-text-muted hover:bg-bg-surface hover:text-text-secondary transition-colors duration-200"
        >
          {maximized ? <Copy size={14} /> : <Square size={14} />}
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => api.close()}
          className="cursor-pointer rounded p-1 text-text-muted hover:bg-red-600/80 hover:text-white hover:shadow-[0_0_12px_rgba(239,68,68,0.3)] transition-all duration-200"
        >
          <X size={14} />
        </motion.button>
      </div>
    </div>
  )
}
