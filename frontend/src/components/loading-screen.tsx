import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'

export function LoadingScreen() {
  const { t } = useTranslation()

  return (
    <div className="flex h-screen flex-col items-center justify-center overflow-hidden relative" style={{ zIndex: 10 }}>
      {/* Logo */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="mb-8"
      >
        <h1 className="font-sans text-5xl font-bold" style={{ color: 'var(--color-accent-gold)' }}>
          {t('app.name')}
        </h1>
      </motion.div>

      {/* Shimmer bar */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        className="mb-4 h-0.5 w-48 overflow-hidden rounded-full"
        style={{ background: 'var(--color-bg-3)' }}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: 'linear-gradient(90deg, transparent, var(--color-accent-gold), transparent)', width: '33%' }}
          initial={{ x: '-100%' }}
          animate={{ x: '300%' }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        />
      </motion.div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.6 }}
        className="text-sm font-sans"
        style={{ color: 'var(--color-text-1)' }}
      >
        {t('app.loading')}
      </motion.p>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.5 }}
        transition={{ delay: 0.6, duration: 0.6 }}
        className="mt-1 text-xs font-sans"
        style={{ color: 'var(--color-text-2)' }}
      >
        {t('app.loadingHint')}
      </motion.p>
    </div>
  )
}
