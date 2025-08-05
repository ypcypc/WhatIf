import { type ReactNode, forwardRef, useRef, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { cn } from '../../utils/cn'

interface AdvancedGlassProps {
  children: ReactNode
  className?: string
  blur?: 'sm' | 'md' | 'lg' | 'xl'
  opacity?: 'low' | 'medium' | 'high'
  border?: boolean
  shadow?: boolean
  animate?: boolean
  onClick?: () => void
  style?: React.CSSProperties
  enableTilt?: boolean
  enableHighlight?: boolean
  enableDisplacement?: boolean
}

// Glass effect variants
const blurVariants = {
  sm: 'backdrop-blur-sm',
  md: 'backdrop-blur-md', 
  lg: 'backdrop-blur-lg',
  xl: 'backdrop-blur-xl'
}

const opacityVariants = {
  low: 'bg-white/5',
  medium: 'bg-white/10',
  high: 'bg-white/20'
}

const borderVariants = {
  low: 'border-white/10',
  medium: 'border-white/25',
  high: 'border-white/40'
}

// Tilt interaction hook
const useTilt = (ref: React.RefObject<HTMLDivElement>, enabled: boolean) => {
  useEffect(() => {
    if (!enabled) return
    
    const el = ref.current
    if (!el) return
    
    const MAX_TILT = 15 // degrees
    
    const handlePointerMove = (e: PointerEvent) => {
      const rect = el.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width - 0.5
      const y = (e.clientY - rect.top) / rect.height - 0.5
      
      // Set CSS variables for tilt
      el.style.setProperty('--rx', `${-y * MAX_TILT}deg`)
      el.style.setProperty('--ry', `${x * MAX_TILT}deg`)
      
      // Set CSS variables for highlight position
      el.style.setProperty('--gx', `${e.clientX - rect.left}px`)
      el.style.setProperty('--gy', `${e.clientY - rect.top}px`)
    }
    
    const handlePointerLeave = () => {
      el.style.removeProperty('--rx')
      el.style.removeProperty('--ry')
      el.style.removeProperty('--gx')
      el.style.removeProperty('--gy')
    }
    
    el.addEventListener('pointermove', handlePointerMove)
    el.addEventListener('pointerleave', handlePointerLeave)
    
    return () => {
      el.removeEventListener('pointermove', handlePointerMove)
      el.removeEventListener('pointerleave', handlePointerLeave)
    }
  }, [enabled])
}

// WebGL support detection
const useWebGLSupport = () => {
  const [supportsWebGL, setSupportsWebGL] = useState(false)
  
  useEffect(() => {
    try {
      const canvas = document.createElement('canvas')
      const gl = canvas.getContext('webgl2') || canvas.getContext('webgl')
      setSupportsWebGL(!!gl)
    } catch {
      setSupportsWebGL(false)
    }
  }, [])
  
  return supportsWebGL
}

// Reduced motion detection
const usePrefersReducedMotion = () => {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
  
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches)
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])
  
  return prefersReducedMotion
}

export const AdvancedGlass = forwardRef<HTMLDivElement, AdvancedGlassProps>(({
  children,
  className,
  blur = 'lg',
  opacity = 'medium',
  border = true,
  shadow = true,
  animate = true,
  onClick,
  style,
  enableTilt = true,
  enableHighlight = true,
  enableDisplacement = false
}, ref) => {
  const internalRef = useRef<HTMLDivElement>(null)
  const glassRef = ref || internalRef
  
  const supportsWebGL = useWebGLSupport()
  const prefersReducedMotion = usePrefersReducedMotion()
  
  // Enable tilt only if not reduced motion
  const shouldEnableTilt = enableTilt && !prefersReducedMotion
  useTilt(glassRef as React.RefObject<HTMLDivElement>, shouldEnableTilt)
  
  const Component = animate ? motion.div : 'div'
  
  const animationProps = animate ? {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { type: 'spring' as const, stiffness: 300, damping: 30 },
    whileHover: { scale: 1.02 },
    whileTap: { scale: 0.97 }
  } : {}

  return (
    <Component
      ref={glassRef}
      className={cn(
        // Layout & isolation
        'relative isolate rounded-[1.25rem] overflow-hidden',
        
        // Glass core effects
        blurVariants[blur],
        opacityVariants[opacity],
        
        // Border with gradient-like effect
        border && ['border', borderVariants[opacity]],
        
        // Shadow
        shadow && 'shadow-lg shadow-black/20',
        
        // Interactive & performance
        'transition-transform duration-200 will-change-transform',
        
        className
      )}
      style={{
        // Safari prefix for backdrop-filter
        WebkitBackdropFilter: `blur(${blur === 'sm' ? '4px' : blur === 'md' ? '8px' : blur === 'lg' ? '16px' : '24px'})`,
        
        // Advanced gradient background
        background: `linear-gradient(135deg, 
          rgba(255,255,255,${opacity === 'low' ? '0.12' : opacity === 'medium' ? '0.22' : '0.35'}), 
          rgba(255,255,255,${opacity === 'low' ? '0.03' : opacity === 'medium' ? '0.06' : '0.1'}))`,
        
        ...style
      }}
      onClick={onClick}
      {...animationProps}
    >
      {/* Tilt effect wrapper - separate from positioning */}
      <div 
        className={cn(
          'w-full h-full',
          shouldEnableTilt && 'glass-tilt'
        )}
        style={{
          ...(shouldEnableTilt && {
            transformStyle: 'preserve-3d'
          })
        }}
      >
        {/* Top highlight layer */}
        <span 
          className={cn(
            'pointer-events-none absolute inset-0 rounded-[inherit]',
            'bg-gradient-to-b from-white/30 to-transparent',
            // Mask to create top-only highlight
            'opacity-60'
          )}
          style={{
            maskImage: 'linear-gradient(to bottom, black 0%, black 45%, transparent 100%)',
            WebkitMaskImage: 'linear-gradient(to bottom, black 0%, black 45%, transparent 100%)'
          }}
        />
        
        {/* Dynamic highlight following cursor */}
        {enableHighlight && shouldEnableTilt && (
          <span 
            className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 hover:opacity-100 transition-opacity duration-300"
            style={{
              background: 'radial-gradient(200px circle at var(--gx,50%) var(--gy,0%), rgba(255,255,255,0.35), transparent 60%)'
            }}
          />
        )}
        
        {/* Inner shadow for depth */}
        <span 
          className="pointer-events-none absolute inset-0 rounded-[inherit]"
          style={{
            boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.18), inset 0 1px 2px rgba(0,0,0,0.1)'
          }}
        />
        
        {/* Content container */}
        <div className="relative z-10 p-6">
          {children}
        </div>
        
        {/* Optional WebGL displacement effect */}
        {enableDisplacement && supportsWebGL && !prefersReducedMotion && (
          <div className="absolute inset-0 pointer-events-none">
            {/* Placeholder for future Pixi.js displacement */}
            <canvas 
              className="absolute inset-0 w-full h-full opacity-30 mix-blend-overlay"
              style={{ 
                background: 'radial-gradient(circle at 30% 70%, rgba(0,150,255,0.1), transparent 50%)'
              }}
            />
          </div>
        )}
      </div>
    </Component>
  )
})

AdvancedGlass.displayName = 'AdvancedGlass'