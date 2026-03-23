import { useRef, useEffect } from 'react'
import { ParticleCanvas } from './particle-canvas'
import type { WhiteHoleHandle } from './particle-canvas'

interface Props {
  whiteHoleRef?: React.RefObject<WhiteHoleHandle | null>
}

export function BackgroundLayers({ whiteHoleRef }: Props) {
  const lightRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!lightRef.current) return
      const W = window.innerWidth, H = window.innerHeight
      const ox = (e.clientX - W / 2) * 0.08
      const oy = (e.clientY - H / 2) * 0.08
      lightRef.current.style.transform = `translate(calc(-50% + ${ox}px), calc(-50% + ${oy}px))`
    }
    window.addEventListener('mousemove', onMouseMove)
    return () => window.removeEventListener('mousemove', onMouseMove)
  }, [])

  return (
    <>
      {/* Particle system */}
      <ParticleCanvas ref={whiteHoleRef} />

      {/* Grid dot overlay */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(rgba(232,160,32,0.04) 1px, transparent 1px)',
          backgroundSize: '44px 44px',
          zIndex: 0,
        }}
      />

      {/* Vignette */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 80% 80% at 50% 50%, transparent 40%, rgba(4,8,15,0.75) 100%)',
          zIndex: 0,
        }}
      />

      {/* Ambient light (follows mouse) */}
      <div
        ref={lightRef}
        className="fixed pointer-events-none"
        style={{
          width: 700,
          height: 700,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(232,160,32,0.05) 0%, transparent 65%)',
          zIndex: 0,
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          transition: 'transform 0.6s cubic-bezier(.16,1,.3,1)',
        }}
      />
    </>
  )
}
