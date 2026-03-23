import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, Check, Loader2, Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { motion } from 'motion/react'
import { getWorldPkgs, loadWorldPkg, importWorldPkg, getWorldPkgCoverUrl, type WorldPkgInfo } from '@/lib/api'

const COVER_GRADIENTS = [
  'linear-gradient(145deg, #0a3d2e 0%, #1a7a5e 50%, #0d4535 100%)',
  'linear-gradient(145deg, #2d1b4e 0%, #5b3a8c 50%, #3d2560 100%)',
  'linear-gradient(145deg, #4a1a1a 0%, #8c3a3a 50%, #5a2020 100%)',
  'linear-gradient(145deg, #3d2e0a 0%, #7a6a1a 50%, #4d3d0d 100%)',
  'linear-gradient(145deg, #0a2d3d 0%, #1a5a7a 50%, #0d3545 100%)',
  'linear-gradient(145deg, #3d0a3d 0%, #7a1a7a 50%, #4d0d4d 100%)',
  'linear-gradient(145deg, #0a3d3d 0%, #1a7a6a 50%, #0d4540 100%)',
  'linear-gradient(145deg, #1a1a2e 0%, #3a3a5c 50%, #252540 100%)',
]

function hashTitle(title: string): number {
  let hash = 0
  for (let i = 0; i < title.length; i++) {
    hash = ((hash << 5) - hash + title.charCodeAt(i)) | 0
  }
  return Math.abs(hash)
}

interface Props {
  currentPkg: string | null
  onSelect: (filename: string, name: string) => void
  onBack: () => void
}

export function LibraryPage({ currentPkg, onSelect, onBack }: Props) {
  const { t } = useTranslation()
  const [packages, setPackages] = useState<WorldPkgInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingPkg, setLoadingPkg] = useState<string | null>(null)
  const [importing, setImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getWorldPkgs()
      .then(data => setPackages(data.packages))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function handleSelect(pkg: WorldPkgInfo) {
    if (loadingPkg) return
    setLoadingPkg(pkg.filename)
    try {
      await loadWorldPkg(pkg.filename)
      onSelect(pkg.filename, pkg.name)
    } catch { /* ignore */ }
    setLoadingPkg(null)
  }

  async function handleImport(file: File) {
    if (!file.name.endsWith('.wpkg')) return
    setImporting(true)
    try {
      await importWorldPkg(file)
      const data = await getWorldPkgs()
      setPackages(data.packages)
    } catch { /* ignore */ }
    setImporting(false)
  }

  return (
    <div className="flex h-full flex-col" style={{ zIndex: 10, position: 'relative' }}>
      {/* Header */}
      <div className="screen-hdr">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={13} />
          {t('settings.back')}
        </button>
        <span className="text-lg font-medium font-sans" style={{ color: 'var(--color-text-0)' }}>
          {t('library.title')}
        </span>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto p-10" style={{ maxWidth: 960, margin: '0 auto', width: '100%' }}>
        {loading ? (
          <div className="flex items-center justify-center h-40 font-sans text-sm" style={{ color: 'var(--color-text-1)' }}>
            <Loader2 size={16} className="animate-spin mr-2" />
            {t('start.loadingPkgs')}
          </div>
        ) : (
          <motion.div
            className="grid gap-5"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(155px, 1fr))' }}
            initial="hidden"
            animate="visible"
            transition={{ staggerChildren: 0.05 }}
          >
            {packages.map(pkg => (
              <BookCard
                key={pkg.filename}
                pkg={pkg}
                isActive={pkg.name === currentPkg}
                isLoading={pkg.filename === loadingPkg}
                onSelect={() => handleSelect(pkg)}
              />
            ))}
            <ImportCard
              onClick={() => fileInputRef.current?.click()}
              importing={importing}
            />
          </motion.div>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".wpkg"
        className="hidden"
        onChange={e => {
          const file = e.target.files?.[0]
          if (file) handleImport(file)
          e.target.value = ''
        }}
      />
    </div>
  )
}

function BookCard({
  pkg, isActive, isLoading, onSelect,
}: {
  pkg: WorldPkgInfo; isActive: boolean; isLoading: boolean; onSelect: () => void
}) {
  const { t } = useTranslation()
  const cardRef = useRef<HTMLDivElement>(null)
  const gradient = COVER_GRADIENTS[hashTitle(pkg.name) % COVER_GRADIENTS.length]
  const firstChar = pkg.name[0] || '?'
  const coverUrl = pkg.hasCover ? getWorldPkgCoverUrl(pkg.filename) : null

  function handleMouseMove(e: React.MouseEvent) {
    const card = cardRef.current!
    const r = card.getBoundingClientRect()
    const x = (e.clientX - r.left) / r.width - 0.5
    const y = (e.clientY - r.top) / r.height - 0.5
    card.style.transform = `perspective(600px) translateY(-8px) scale(1.03) rotateY(${x * 14}deg) rotateX(${-y * 14}deg)`
  }

  function handleMouseLeave() {
    cardRef.current!.style.transform = ''
  }

  return (
    <motion.div
      ref={cardRef}
      variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="book-card"
    >
      {/* Cover */}
      <div
        className="relative flex items-center justify-center overflow-hidden"
        style={{ aspectRatio: '3/4', background: coverUrl ? '#0a0a1a' : gradient }}
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={pkg.name}
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <>
            {/* Light overlay */}
            <div
              className="absolute inset-0"
              style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.06) 0%, transparent 40%, rgba(0,0,0,0.4) 100%)' }}
            />
            <span
              className="relative z-[1] text-[54px] font-bold select-none"
              style={{ fontFamily: "'Playfair Display', serif", color: 'rgba(255,255,255,0.8)', textShadow: '0 0 40px rgba(255,255,255,0.3)' }}
            >
              {firstChar}
            </span>
          </>
        )}

        {/* Hover overlay with actions */}
        <div className="book-overlay">
          <button className="book-action-btn" onClick={onSelect}>
            {t('library.select', '选择')}
          </button>
        </div>

        {/* Active badge */}
        {isActive && (
          <div className="absolute top-2 right-2 z-[3] rounded-full p-0.5" style={{ background: 'var(--color-accent-gold)' }}>
            <Check size={12} style={{ color: 'var(--color-bg-primary)' }} />
          </div>
        )}

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 z-[3] flex items-center justify-center bg-black/50">
            <Loader2 size={24} className="animate-spin" style={{ color: 'var(--color-accent-gold)' }} />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 pt-3" style={{ background: 'var(--color-bg-3)', borderTop: '0.5px solid var(--color-border)' }}>
        <div className="text-sm font-medium font-sans truncate" style={{ color: 'var(--color-text-0)' }}>
          {pkg.name}
        </div>
        <div className="text-xs font-sans mt-0.5" style={{ color: 'var(--color-text-1)' }}>
          {t('start.worldPkgSize', { size: (pkg.size / 1024).toFixed(0) })}
        </div>
      </div>
    </motion.div>
  )
}

function ImportCard({ onClick, importing }: { onClick: () => void; importing: boolean }) {
  const { t } = useTranslation()
  return (
    <motion.div
      variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      onClick={onClick}
      className="import-card cursor-pointer"
      style={{ aspectRatio: '3/5.2' }}
    >
      {importing ? (
        <Loader2 size={28} className="animate-spin" style={{ color: 'var(--color-accent-gold)' }} />
      ) : (
        <Plus size={28} style={{ color: 'var(--color-text-2)' }} />
      )}
      <span className="text-[13px] font-sans" style={{ color: 'var(--color-text-2)' }}>
        {importing ? t('library.importing') : t('library.import')}
      </span>
    </motion.div>
  )
}
