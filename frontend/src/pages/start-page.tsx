import { useState, useEffect, useRef, useCallback } from 'react'
import { Play, BookOpen, FolderOpen, Settings } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { PixelLogo } from '@/components/pixel-logo'
import type { WhiteHoleHandle } from '@/components/particle-canvas'

interface Props {
  currentPkg: string | null
  needsApiKey?: boolean
  onStartGame: () => void
  onSelectPkg: () => void
  onLoadSave: () => void
  onSettings: () => void
  whiteHoleRef?: React.RefObject<WhiteHoleHandle | null>
}

const MENU_ITEMS = [
  { key: 'selectPkg', icon: BookOpen, labelKey: 'start.noPkgSelected', action: 'onSelectPkg' },
  { key: 'startGame', icon: Play, labelKey: 'start.startGame', action: 'onStartGame' },
  { key: 'loadSave', icon: FolderOpen, labelKey: 'start.loadSave', action: 'onLoadSave' },
  { key: 'settings', icon: Settings, labelKey: 'start.settings', action: 'onSettings' },
] as const

// ══════════════════════════════
//  GLASS BUTTON with edge glare + specular dot + 3D tilt
// ══════════════════════════════
function GlassButton({
  children,
  disabled,
  visible,
  className,
  onClick,
  onMouseDown,
}: {
  children: React.ReactNode
  disabled?: boolean
  visible: boolean
  className?: string
  onClick?: () => void
  onMouseDown?: () => void
}) {
  const btnRef = useRef<HTMLButtonElement>(null)
  const specRef = useRef<HTMLDivElement>(null)
  const specDotRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef(0)
  const angleRef = useRef({ current: 135, target: 135 })

  const lerpAngle = useCallback((a: number, b: number, t: number) => {
    let diff = b - a
    while (diff > 180) diff -= 360
    while (diff < -180) diff += 360
    return a + diff * t
  }, [])

  const startAngleLerp = useCallback(() => {
    function animate() {
      const a = angleRef.current
      a.current = lerpAngle(a.current, a.target, 0.12)
      const btn = btnRef.current
      if (btn) {
        const edge = btn.querySelector('.glass-edge') as HTMLElement
        const glow = btn.querySelector('.glass-edge-glow') as HTMLElement
        const deg = a.current + 'deg'
        if (edge) edge.style.setProperty('--edge-angle', deg)
        if (glow) glow.style.setProperty('--edge-angle', deg)
      }
      rafRef.current = requestAnimationFrame(animate)
    }
    if (!rafRef.current) rafRef.current = requestAnimationFrame(animate)
  }, [lerpAngle])

  const stopAngleLerp = useCallback(() => {
    if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = 0 }
  }, [])

  useEffect(() => () => stopAngleLerp(), [stopAngleLerp])

  const handleMouseEnter = useCallback(() => {
    if (disabled) return
    if (specRef.current) specRef.current.style.opacity = '1'
    startAngleLerp()
  }, [disabled, startAngleLerp])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (disabled || !btnRef.current) return
    const r = btnRef.current.getBoundingClientRect()
    const x = e.clientX - r.left
    const y = e.clientY - r.top
    const nx = x / r.width - 0.5
    const ny = y / r.height - 0.5

    // Edge angle: opposite side of mouse (light source behind mouse)
    angleRef.current.target = Math.atan2(ny, nx) * (180 / Math.PI) + 180

    // Specular dot follows mouse
    if (specDotRef.current) {
      specDotRef.current.style.left = x + 'px'
      specDotRef.current.style.top = y + 'px'
    }

    // 3D perspective tilt
    btnRef.current.style.transform =
      `translateX(4px) scale(1.018) perspective(900px) rotateY(${nx * 3.5}deg) rotateX(${-ny * 5}deg)`
  }, [disabled])

  const handleMouseLeave = useCallback(() => {
    if (specRef.current) specRef.current.style.opacity = '0'
    if (btnRef.current) btnRef.current.style.transform = ''
    stopAngleLerp()
  }, [stopAngleLerp])

  return (
    <button
      ref={btnRef}
      onClick={disabled ? undefined : onClick}
      onMouseDown={disabled ? undefined : onMouseDown}
      onMouseEnter={handleMouseEnter}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={className}
      disabled={disabled}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateX(0)' : 'translateX(-28px)',
      }}
    >
      {/* Glass effect layers */}
      <div className="glass-edge" />
      <div className="glass-edge-glow" />
      <div className="glass-refract" />

      {/* Specular dot (mouse-following highlight) */}
      <div
        ref={specRef}
        style={{
          position: 'absolute', inset: 0, borderRadius: 16,
          pointerEvents: 'none', zIndex: 1,
          opacity: 0, transition: 'opacity 0.4s ease',
          overflow: 'hidden',
        }}
      >
        <div
          ref={specDotRef}
          style={{
            position: 'absolute', width: 180, height: 180, borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(255,245,210,0.13) 0%, rgba(232,160,32,0.06) 35%, transparent 70%)',
            transform: 'translate(-50%, -50%)',
            pointerEvents: 'none', filter: 'blur(6px)',
          }}
        />
      </div>

      {children}
    </button>
  )
}

// ══════════════════════════════
//  START PAGE
// ══════════════════════════════
export function StartPage({ currentPkg, needsApiKey, onStartGame, onSelectPkg, onLoadSave, onSettings, whiteHoleRef }: Props) {
  const { t } = useTranslation()
  const [phase, setPhase] = useState<'logo' | 'tagline' | 'menu' | 'done'>('logo')
  const [visibleBtns, setVisibleBtns] = useState(0)

  const canStart = currentPkg !== null && !needsApiKey
  const actions: Record<string, () => void> = { onStartGame, onSelectPkg, onLoadSave, onSettings }

  function handleLogoComplete() {
    setPhase('tagline')
    setTimeout(() => setPhase('menu'), 400)
  }

  useEffect(() => {
    if (phase !== 'menu') return
    let i = 0
    const interval = setInterval(() => {
      i++
      setVisibleBtns(i)
      if (i >= MENU_ITEMS.length) {
        clearInterval(interval)
        setTimeout(() => setPhase('done'), 200)
      }
    }, 130)
    return () => clearInterval(interval)
  }, [phase])

  return (
    <div className="relative flex h-full flex-col items-center justify-center overflow-hidden" style={{ zIndex: 10 }}>
      {/* Logo */}
      <div className="mb-14 text-center">
        <PixelLogo onRevealComplete={handleLogoComplete} />
        <p
          className="font-sans text-[15px] tracking-[0.12em] mt-5 transition-opacity duration-[900ms]"
          style={{
            color: 'var(--color-text-1)',
            opacity: phase === 'logo' ? 0 : 1,
          }}
        >
          {t('start.subtitle')}
        </p>
      </div>

      {/* Menu */}
      <div className="flex flex-col gap-[14px] w-[380px]">
        {MENU_ITEMS.map((item, idx) => {
          const Icon = item.icon
          const isStartGame = item.key === 'startGame'
          const isSelectPkg = item.key === 'selectPkg'
          const isDim = isStartGame && !canStart
          const visible = visibleBtns > idx || phase === 'done'
          const label = isSelectPkg && currentPkg
            ? t('start.currentPkg', { name: currentPkg })
            : t(item.labelKey)

          return (
            <GlassButton
              key={item.key}
              onClick={isDim ? undefined : actions[item.action]}
              onMouseDown={() => whiteHoleRef?.current?.triggerExplosion()}
              className={`mbtn ${isDim ? 'dim' : ''} ${visible ? 'in' : ''}`}
              disabled={isDim}
              visible={visible}
            >
              <div className="mbtn-icon">
                <Icon size={17} />
              </div>
              <span className="mbtn-label">{label}</span>
            </GlassButton>
          )
        })}
      </div>

      {/* API key warning */}
      {needsApiKey && (
        <div
          className="warn-badge mt-6 transition-opacity duration-[900ms]"
          style={{ opacity: phase === 'done' ? 1 : 0 }}
        >
          <span className="warn-dot" />
          {t('start.needsApiKey')}
        </div>
      )}

      {/* Version */}
      <span
        className="absolute bottom-6 text-xs font-sans transition-opacity duration-1000"
        style={{
          color: 'var(--color-text-2)',
          opacity: phase === 'done' ? 0.3 : 0,
        }}
      >
        v0.1.0
      </span>
    </div>
  )
}
