import { useRef, useEffect, useCallback } from 'react'

interface Props {
  onRevealComplete?: () => void
}

const FONT_SZ = 96
const SAMPLE = 8
const PX = 6
const GAP = 2
const STEP = PX + GAP
const TEXT = 'WhatIf'
const FONT_FAMILY = 'WhatIf Pixel Logo'
const FONT = `${FONT_SZ}px '${FONT_FAMILY}'`
const COL_STAGGER = 38
const ROW_STAGGER = 18
const FADE_DURATION = 160

function amberColor(bc: number, totalCols: number, alpha: number, shimmer: number): string {
  const phase = ((bc / totalCols) + shimmer) % 1.0
  const bright = 0.5 + 0.5 * Math.sin(phase * Math.PI * 2)
  const r = Math.round(180 + bright * 75)
  const g = Math.round(100 + bright * 80)
  const b = Math.round(0 + bright * 30)
  return `rgba(${r},${g},${b},${alpha})`
}

function bloomColor(bc: number, totalCols: number, alpha: number, shimmer: number): string {
  const phase = ((bc / totalCols) + shimmer) % 1.0
  const bright = 0.5 + 0.5 * Math.sin(phase * Math.PI * 2)
  const r = Math.round(200 + bright * 55)
  const g = Math.round(120 + bright * 60)
  return `rgba(${r},${g},10,${alpha * 0.18})`
}

export function PixelLogo({ onRevealComplete }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef(0)
  const timeoutRefs = useRef<number[]>([])
  const revealFired = useRef(false)
  const onRevealRef = useRef(onRevealComplete)

  useEffect(() => {
    onRevealRef.current = onRevealComplete
  }, [onRevealComplete])

  const clearTimers = useCallback(() => {
    for (const timeoutId of timeoutRefs.current) {
      window.clearTimeout(timeoutId)
    }
    timeoutRefs.current = []
  }, [])

  const setup = useCallback(() => {
    const lc = canvasRef.current!
    const lx = lc.getContext('2d')!

    const off = document.createElement('canvas')
    const ox = off.getContext('2d')!
    ox.font = FONT
    const tw = Math.ceil(ox.measureText(TEXT).width)
    const th = FONT_SZ + 24
    off.width = tw + 16
    off.height = th + 16

    ox.font = FONT
    ox.fillStyle = '#ffffff'
    ox.textBaseline = 'top'
    ox.fillText(TEXT, 8, 10)

    const imgData = ox.getImageData(0, 0, off.width, off.height).data
    const ow = off.width, oh = off.height

    const blockCols = Math.ceil(ow / SAMPLE)
    const blockRows = Math.ceil(oh / SAMPLE)
    const lit: { bc: number; br: number }[] = []
    const litByCol: Record<number, number[]> = {}

    for (let br = 0; br < blockRows; br++) {
      for (let bc = 0; bc < blockCols; bc++) {
        let found = false
        const cx = bc * SAMPLE + Math.floor(SAMPLE / 2)
        const cy = br * SAMPLE + Math.floor(SAMPLE / 2)
        outer:
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const sx = cx + dx, sy = cy + dy
            if (sx < 0 || sx >= ow || sy < 0 || sy >= oh) continue
            if (imgData[(sy * ow + sx) * 4 + 3] > 80) { found = true; break outer }
          }
        }
        if (found) {
          lit.push({ bc, br })
          if (!litByCol[bc]) litByCol[bc] = []
          litByCol[bc].push(br)
        }
      }
    }

    const canvasW = blockCols * STEP - GAP
    const canvasH = blockRows * STEP - GAP
    lc.width = canvasW
    lc.height = canvasH

    function applyScale() {
      const targetW = Math.min(560, Math.max(260, window.innerWidth * 0.55))
      const s = targetW / canvasW
      lc.style.width = Math.round(canvasW * s) + 'px'
      lc.style.height = Math.round(canvasH * s) + 'px'
    }
    applyScale()
    window.addEventListener('resize', applyScale)

    const alphaMap = new Float32Array(blockCols * blockRows)
    let shimmer = 0

    function draw() {
      lx.clearRect(0, 0, canvasW, canvasH)
      for (const { bc, br } of lit) {
        const a = alphaMap[br * blockCols + bc]
        if (a <= 0) continue
        const x = bc * STEP, y = br * STEP

        lx.fillStyle = bloomColor(bc, blockCols, a, shimmer)
        lx.fillRect(x - 2, y - 2, PX + 4, PX + 4)

        lx.fillStyle = amberColor(bc, blockCols, a, shimmer)
        lx.fillRect(x, y, PX, PX)

        if (a > 0.7) {
          lx.fillStyle = `rgba(255,240,180,${(a - 0.7) * 0.9})`
          lx.fillRect(x, y, 2, 2)
        }
      }
      shimmer = (shimmer + 0.0025) % 1
      rafRef.current = requestAnimationFrame(draw)
    }

    const uniqueCols = Object.keys(litByCol).map(Number).sort((a, b) => a - b)

    const schedule = (callback: () => void, delay: number) => {
      const timeoutId = window.setTimeout(callback, delay)
      timeoutRefs.current.push(timeoutId)
    }

    schedule(() => {
      lc.style.opacity = '1'
      lc.style.transform = 'translateY(0)'
      rafRef.current = requestAnimationFrame(draw)

      uniqueCols.forEach((bc, ci) => {
        const rows = litByCol[bc].slice().sort((a, b) => a - b)
        rows.forEach((br, ri) => {
          const delay = ci * COL_STAGGER + ri * ROW_STAGGER
          schedule(() => {
            const idx = br * blockCols + bc
            const start = performance.now()
            function fadeIn(now: number) {
              const t = Math.min(1, (now - start) / FADE_DURATION)
              alphaMap[idx] = t
              if (t < 1) requestAnimationFrame(fadeIn)
            }
            requestAnimationFrame(fadeIn)
          }, delay)
        })
      })

      const totalReveal = uniqueCols.length * COL_STAGGER + 200
      schedule(() => {
        if (!revealFired.current) {
          revealFired.current = true
          onRevealRef.current?.()
        }
      }, totalReveal)
    }, 280)

    return () => {
      window.removeEventListener('resize', applyScale)
      clearTimers()
    }
  }, [clearTimers])

  useEffect(() => {
    let cleanup: (() => void) | undefined
    let isActive = true

    async function setupLogo() {
      if (!('fonts' in document)) {
        if (canvasRef.current) {
          cleanup = setup()
        }
        return
      }

      await document.fonts.load(FONT, TEXT)

      if (!isActive || !canvasRef.current) return

      cleanup = setup()
    }

    void setupLogo()

    return () => {
      isActive = false
      cancelAnimationFrame(rafRef.current)
      clearTimers()
      cleanup?.()
    }
  }, [clearTimers, setup])

  return (
    <div ref={wrapRef} className="relative inline-block">
      <canvas
        ref={canvasRef}
        style={{
          display: 'block',
          margin: '0 auto',
          imageRendering: 'pixelated',
          opacity: 0,
          transform: 'translateY(32px)',
          transition: 'opacity 0.6s ease, transform 0.8s cubic-bezier(.16,1,.3,1)',
          filter: 'drop-shadow(0 0 6px rgba(232,160,32,0.9)) drop-shadow(0 0 22px rgba(232,160,32,0.5)) drop-shadow(0 0 55px rgba(200,120,10,0.3))',
        }}
      />
      {/* Scanlines overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.18) 3px, rgba(0,0,0,0.18) 4px)',
        }}
      />
    </div>
  )
}
