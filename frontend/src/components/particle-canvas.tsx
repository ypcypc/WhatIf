import { useRef, useEffect, forwardRef, useImperativeHandle } from 'react'

// ══════════════════════════════
//  TYPES
// ══════════════════════════════
type Phase = 'idle' | 'shrinking' | 'exploding' | 'recovering'

interface WHState {
  baseR: number
  r: number
  tr: number
  bright: number
  tBright: number
  rotY: number
  rotX: number
  phase: Phase
  shrinkTimer: number
  explodeForce: number
  recoverT: number
}

export interface WhiteHoleHandle {
  triggerExplosion: () => void
}

// ══════════════════════════════
//  KEPLER MATH (pure functions)
// ══════════════════════════════
function solveKepler(M: number, e: number): number {
  M = M % (Math.PI * 2)
  if (M < 0) M += Math.PI * 2
  let E = M + e * Math.sin(M)
  for (let i = 0; i < 12; i++) {
    const dE = (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E))
    E -= dE
    if (Math.abs(dE) < 1e-8) break
  }
  return E
}

function trueAnomaly(E: number, e: number): number {
  return 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2))
}

function orbitalRadius(a: number, e: number, nu: number): number {
  return a * (1 - e * e) / (1 + e * Math.cos(nu))
}

function project3D(x: number, y: number, z: number, ry: number, rx: number) {
  const cosY = Math.cos(ry), sinY = Math.sin(ry)
  const x1 = x * cosY + z * sinY
  const z1 = -x * sinY + z * cosY
  const cosX = Math.cos(rx), sinX = Math.sin(rx)
  const y2 = y * cosX - z1 * sinX
  const z2 = y * sinX + z1 * cosX
  return { px: x1, py: y2, pz: z2 }
}

// ══════════════════════════════
//  PARTICLE DATA GENERATORS
// ══════════════════════════════
const CORE_N = 4500
const ORB_N = 2200
const DUST_N = 400

interface CoreData {
  basePositions: Float32Array // bx, by, bz (normalized sphere coords)
  positions: Float32Array     // sx, sy (screen coords mapped to 3D)
  velocities: Float32Array    // evx, evy
  frozen: Float32Array        // frozenX, frozenY
  noise: Float32Array         // nPhase, nSpd, nAmp
  props: Float32Array         // sz, br, rFact, isInner(0/1)
}

interface OrbData {
  elements: Float32Array      // a, e, incl, omega, Omega, M0, n, M (8 per particle)
  positions: Float32Array     // sx, sy, prevSx, prevSy
  velocities: Float32Array    // evx, evy
  frozen: Float32Array
  props: Float32Array         // sz, br, isRing(0/1), trail, exploded(0/1)
  brownian: Float32Array      // bnx, bny, bvx, bvy
}

interface DustData {
  positions: Float32Array     // x, y (normalized -1..1)
  velocities: Float32Array    // vx, vy
  props: Float32Array         // sz, br, ph
}

function createCoreData(): CoreData {
  const base = new Float32Array(CORE_N * 3)
  const pos = new Float32Array(CORE_N * 2)
  const vel = new Float32Array(CORE_N * 2)
  const frz = new Float32Array(CORE_N * 2)
  const noi = new Float32Array(CORE_N * 3)
  const prp = new Float32Array(CORE_N * 4)

  for (let i = 0; i < CORE_N; i++) {
    const u = Math.random()
    let rr: number
    if (u < 0.40) rr = Math.cbrt(Math.random()) * 0.5
    else if (u < 0.75) rr = 0.5 + Math.random() * 0.35
    else rr = 0.85 + Math.random() * 0.15

    const theta = Math.acos(2 * Math.random() - 1)
    const phi = Math.random() * Math.PI * 2
    base[i * 3] = rr * Math.sin(theta) * Math.cos(phi)
    base[i * 3 + 1] = rr * Math.sin(theta) * Math.sin(phi)
    base[i * 3 + 2] = rr * Math.cos(theta)

    noi[i * 3] = Math.random() * Math.PI * 2
    noi[i * 3 + 1] = 0.4 + Math.random() * 1.5
    noi[i * 3 + 2] = 0.003 + Math.random() * 0.012

    const isInner = rr < 0.5
    prp[i * 4] = isInner ? (0.5 + Math.random() * 1.2) : (0.4 + Math.random() * 1.6)
    prp[i * 4 + 1] = isInner ? (0.6 + Math.random() * 0.4) : (0.3 + Math.random() * 0.7)
    prp[i * 4 + 2] = rr
    prp[i * 4 + 3] = isInner ? 1 : 0
  }

  return { basePositions: base, positions: pos, velocities: vel, frozen: frz, noise: noi, props: prp }
}

function createOrbData(): OrbData {
  const elem = new Float32Array(ORB_N * 8)
  const pos = new Float32Array(ORB_N * 4)
  const vel = new Float32Array(ORB_N * 2)
  const frz = new Float32Array(ORB_N * 2)
  const prp = new Float32Array(ORB_N * 5)
  const brn = new Float32Array(ORB_N * 4)

  for (let i = 0; i < ORB_N; i++) {
    const ringBand = Math.random() < 0.55
    const a = ringBand ? 1.05 + Math.random() * 0.6 : 1.2 + Math.random() * 2.5
    const e = ringBand ? 0.02 + Math.random() * 0.15 : 0.05 + Math.random() * 0.75
    const incl = ringBand ? (Math.random() - 0.5) * 0.12 : (Math.random() - 0.5) * Math.PI * 0.7
    const omega = Math.random() * Math.PI * 2
    const Omega = Math.random() * Math.PI * 2
    const M0 = Math.random() * Math.PI * 2
    const n = 0.008 / Math.pow(a, 1.5)

    const idx = i * 8
    elem[idx] = a; elem[idx + 1] = e; elem[idx + 2] = incl
    elem[idx + 3] = omega; elem[idx + 4] = Omega
    elem[idx + 5] = M0; elem[idx + 6] = n; elem[idx + 7] = M0

    prp[i * 5] = ringBand ? (0.4 + Math.random() * 1.2) : (0.5 + Math.random() * 2.0)
    prp[i * 5 + 1] = ringBand ? (0.5 + Math.random() * 0.5) : (0.15 + Math.random() * 0.6)
    prp[i * 5 + 2] = ringBand ? 1 : 0
    prp[i * 5 + 3] = ringBand ? 0.5 + Math.random() * 0.5 : 0
    prp[i * 5 + 4] = 0
  }

  return { elements: elem, positions: pos, velocities: vel, frozen: frz, props: prp, brownian: brn }
}

function createDustData(): DustData {
  const pos = new Float32Array(DUST_N * 2)
  const vel = new Float32Array(DUST_N * 2)
  const prp = new Float32Array(DUST_N * 3)

  for (let i = 0; i < DUST_N; i++) {
    pos[i * 2] = Math.random() * 2 - 1
    pos[i * 2 + 1] = Math.random() * 2 - 1
    vel[i * 2] = (Math.random() - 0.5) * 0.0004
    vel[i * 2 + 1] = (Math.random() - 0.5) * 0.0004
    prp[i * 3] = 0.3 + Math.random() * 1.0
    prp[i * 3 + 1] = 0.04 + Math.random() * 0.12
    prp[i * 3 + 2] = Math.random() * Math.PI * 2
  }

  return { positions: pos, velocities: vel, props: prp }
}

// ══════════════════════════════
//  NEAREST BUTTON DISTANCE
// ══════════════════════════════
function nearestBtnDist(mx: number, my: number): number {
  const btns = document.querySelectorAll('.mbtn')
  let minD = Infinity
  btns.forEach(b => {
    const r = b.getBoundingClientRect()
    const bx = r.left + r.width / 2, by = r.top + r.height / 2
    const dx = mx - bx, dy = my - by
    minD = Math.min(minD, Math.sqrt(dx * dx + dy * dy))
  })
  return minD
}

// ══════════════════════════════
//  CANVAS 2D WHITE HOLE SCENE
//  (Renders on a 2D canvas overlay,
//   bloom handled by R3F EffectComposer
//   on a separate THREE.js layer)
// ══════════════════════════════

function WhiteHoleCanvas({ whRef }: { whRef: React.RefObject<WHState | null> }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouseRef = useRef({ x: -9999, y: -9999 })
  const frameRef = useRef(0)
  const coreRef = useRef<CoreData | null>(null)
  const orbRef = useRef<OrbData | null>(null)
  const dustRef = useRef<DustData | null>(null)
  const rafRef = useRef(0)

  useEffect(() => {
    const canvas = canvasRef.current!
    const ctx = canvas.getContext('2d')!
    let W = 0, H = 0

    coreRef.current = createCoreData()
    orbRef.current = createOrbData()
    dustRef.current = createDustData()

    function resize() {
      W = canvas.width = window.innerWidth
      H = canvas.height = window.innerHeight
      if (whRef.current) {
        whRef.current.baseR = Math.max(200, W * 0.35)
      }
    }

    function onMouseMove(e: MouseEvent) {
      mouseRef.current = { x: e.clientX, y: e.clientY }
    }
    function onMouseLeave() {
      mouseRef.current = { x: -9999, y: -9999 }
    }

    function orbitalPos(elemIdx: number, whR: number) {
      const el = orbRef.current!.elements
      const idx = elemIdx * 8
      const a = el[idx], e = el[idx + 1], incl = el[idx + 2]
      const omega = el[idx + 3], Omega = el[idx + 4]
      const M = el[idx + 7]

      const E = solveKepler(M, e)
      const nu = trueAnomaly(E, e)
      const r = orbitalRadius(a, e, nu) * whR

      const xp = r * Math.cos(nu), yp = r * Math.sin(nu)
      const cw = Math.cos(omega), sw = Math.sin(omega)
      const x1 = xp * cw - yp * sw, y1 = xp * sw + yp * cw
      const ci = Math.cos(incl), si = Math.sin(incl)
      const x2 = x1, y2 = y1 * ci, z2 = y1 * si
      const cO = Math.cos(Omega), sO = Math.sin(Omega)
      return { x: x2 * cO - y2 * sO, y: x2 * sO + y2 * cO, z: z2 }
    }

    function detonateNow() {
      const wh = whRef.current!
      const core = coreRef.current!
      const orb = orbRef.current!
      wh.phase = 'exploding'
      wh.explodeForce = 1
      wh.tr = wh.r
      wh.tBright = 2.5
      const cx = W * 0.5, cy = H * 0.42

      for (let i = 0; i < CORE_N; i++) {
        core.frozen[i * 2] = core.positions[i * 2]
        core.frozen[i * 2 + 1] = core.positions[i * 2 + 1]
        const dx = core.positions[i * 2] - cx, dy = core.positions[i * 2 + 1] - cy
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.1
        const isInner = core.props[i * 4 + 3] > 0.5
        if (isInner && Math.random() < 0.15) {
          const driftAng = Math.random() * Math.PI * 2
          core.velocities[i * 2] = Math.cos(driftAng) * Math.random() * 3
          core.velocities[i * 2 + 1] = Math.sin(driftAng) * Math.random() * 3
          continue
        }
        const distNorm = Math.min(1, dist / (wh.r || 30))
        const radialAng = Math.atan2(dy, dx)
        const angSpread = (1 - distNorm) * 2.5 + 0.4
        const ang = radialAng + (Math.random() - 0.5) * angSpread
        const f = 4 + distNorm * 22 + Math.random() * 16
        core.velocities[i * 2] = Math.cos(ang) * f + (Math.random() - 0.5) * 6
        core.velocities[i * 2 + 1] = Math.sin(ang) * f + (Math.random() - 0.5) * 6
      }

      for (let i = 0; i < ORB_N; i++) {
        orb.frozen[i * 2] = orb.positions[i * 2]
        orb.frozen[i * 2 + 1] = orb.positions[i * 2 + 1]
        const dx = orb.positions[i * 2] - cx, dy = orb.positions[i * 2 + 1] - cy
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.1
        const isRing = orb.props[i * 5 + 2] > 0.5
        if (isRing && Math.random() < 0.10) {
          const driftAng = Math.random() * Math.PI * 2
          orb.velocities[i * 2] = Math.cos(driftAng) * (2 + Math.random() * 4)
          orb.velocities[i * 2 + 1] = Math.sin(driftAng) * (2 + Math.random() * 4)
          orb.props[i * 5 + 4] = 1
          continue
        }
        const distNorm = Math.min(1, dist / (wh.r * 2 || 60))
        const ang = Math.atan2(dy, dx) + (Math.random() - 0.5) * 0.6
        const f = 8 + distNorm * 20 + Math.random() * 18
        orb.velocities[i * 2] = Math.cos(ang) * f + (Math.random() - 0.5) * 5
        orb.velocities[i * 2 + 1] = Math.sin(ang) * f + (Math.random() - 0.5) * 5
        orb.props[i * 5 + 4] = 1
      }
    }

    function renderFrame() {
      frameRef.current++
      const frame = frameRef.current
      ctx.clearRect(0, 0, W, H)

      const wh = whRef.current!
      const core = coreRef.current!
      const orb = orbRef.current!
      const dust = dustRef.current!
      const mouse = mouseRef.current
      const cx = W * 0.5, cy = H * 0.42

      // ── Rotation ──
      wh.rotY += 0.003
      if (mouse.x > 0) {
        const mx = (mouse.x / W - 0.5) * 0.4
        const my = (mouse.y / H - 0.5) * 0.2
        wh.rotY += mx * 0.008
        wh.rotX += (0.35 + my * 0.5 - wh.rotX) * 0.02
      }

      // ── Phase FSM ──
      if (wh.phase === 'shrinking') {
        wh.shrinkTimer--
        if (wh.shrinkTimer <= 0) detonateNow()
      }
      if (wh.phase === 'exploding') {
        wh.explodeForce *= 0.950
        wh.tr = 25 + (1 - wh.explodeForce) * 60
        wh.tBright = 0.15 + wh.explodeForce * 2.5
        if (wh.explodeForce < 0.005) {
          wh.phase = 'recovering'
          wh.recoverT = 0
        }
      }
      if (wh.phase === 'recovering') {
        wh.recoverT += 0.008
        wh.tr = wh.baseR
        wh.tBright = 0.30
        if (wh.recoverT >= 1.2) {
          wh.phase = 'idle'
          for (let i = 0; i < ORB_N; i++) {
            orb.props[i * 5 + 4] = 0
            orb.velocities[i * 2] = 0; orb.velocities[i * 2 + 1] = 0
            orb.brownian[i * 4] = 0; orb.brownian[i * 4 + 1] = 0
          }
          for (let i = 0; i < CORE_N; i++) {
            core.velocities[i * 2] = 0; core.velocities[i * 2 + 1] = 0
          }
        }
      }

      // ── Mouse → button distance → radius/brightness ──
      if (wh.phase === 'idle') {
        const dist = nearestBtnDist(mouse.x, mouse.y)
        const maxD = Math.max(400, Math.min(W, H) * 0.5)
        const frac = Math.min(1, dist / maxD)
        wh.tr = 35 + frac * (wh.baseR - 35)
        wh.tBright = 1.1 - frac * 0.80
        if (mouse.x < 0) { wh.tr = wh.baseR; wh.tBright = 0.30 }
      }

      // ── Lerp ──
      wh.r += (wh.tr - wh.r) * 0.05
      const brightSpd = (wh.phase === 'shrinking' || wh.phase === 'exploding') ? 0.12 : 0.055
      wh.bright += (wh.tBright - wh.bright) * brightSpd

      const R = wh.r
      const B = wh.bright
      const glowMult = wh.phase === 'exploding' ? Math.max(0.15, wh.explodeForce * 0.4) : 1
      const coreMult = wh.phase === 'exploding' ? Math.max(0.3, wh.explodeForce * 0.8) : 1

      // ══════════════════════════════
      //  GLOW LAYERS
      // ══════════════════════════════
      const h1R = R * 5
      const g1 = ctx.createRadialGradient(cx, cy, 0, cx, cy, h1R)
      g1.addColorStop(0, `rgba(255,210,120,${0.06 * B * glowMult})`)
      g1.addColorStop(0.25, `rgba(232,160,32,${0.035 * B * glowMult})`)
      g1.addColorStop(1, 'transparent')
      ctx.fillStyle = g1
      ctx.fillRect(cx - h1R, cy - h1R, h1R * 2, h1R * 2)

      const h2R = R * 2.5
      const g2 = ctx.createRadialGradient(cx, cy, 0, cx, cy, h2R)
      g2.addColorStop(0, `rgba(255,235,180,${0.15 * B * glowMult})`)
      g2.addColorStop(0.4, `rgba(232,170,50,${0.06 * B * glowMult})`)
      g2.addColorStop(1, 'transparent')
      ctx.fillStyle = g2
      ctx.fillRect(cx - h2R, cy - h2R, h2R * 2, h2R * 2)

      const h3R = R * 1.2
      const g3 = ctx.createRadialGradient(cx, cy, 0, cx, cy, h3R)
      g3.addColorStop(0, `rgba(255,250,230,${0.20 * B * coreMult})`)
      g3.addColorStop(0.5, `rgba(255,220,150,${0.09 * B * coreMult})`)
      g3.addColorStop(1, 'transparent')
      ctx.fillStyle = g3
      ctx.fillRect(cx - h3R, cy - h3R, h3R * 2, h3R * 2)

      if (B > 0.15) {
        const h4R = R * 0.35
        const g4 = ctx.createRadialGradient(cx, cy, 0, cx, cy, h4R)
        g4.addColorStop(0, `rgba(255,255,255,${Math.min(0.7, 0.30 * B * coreMult)})`)
        g4.addColorStop(0.3, `rgba(255,245,220,${0.15 * B * coreMult})`)
        g4.addColorStop(1, 'transparent')
        ctx.fillStyle = g4
        ctx.fillRect(cx - h4R, cy - h4R, h4R * 2, h4R * 2)
      }

      // ══════════════════════════════
      //  COLLECT DRAW LIST (depth sort)
      // ══════════════════════════════
      const drawList: { x: number; y: number; z: number; sz: number; br: number; trail: number; px: number; py: number; type: 'core' | 'orb'; isInner: boolean; isRing: boolean }[] = []

      // ── Orbital particles ──
      for (let i = 0; i < ORB_N; i++) {
        const eidx = i * 8
        orb.elements[eidx + 7] += orb.elements[eidx + 6] // M += n
        const pidx = i * 4
        orb.positions[pidx + 2] = orb.positions[pidx] // prevSx
        orb.positions[pidx + 3] = orb.positions[pidx + 1] // prevSy

        const pos = orbitalPos(i, R)
        const pr = project3D(pos.x, pos.y, pos.z, wh.rotY, wh.rotX)
        const targetX = cx + pr.px, targetY = cy + pr.py
        const exploded = orb.props[i * 5 + 4] > 0.5

        if (wh.phase === 'exploding' && exploded) {
          orb.positions[pidx] += orb.velocities[i * 2]
          orb.positions[pidx + 1] += orb.velocities[i * 2 + 1]
          orb.velocities[i * 2] *= 0.970
          orb.velocities[i * 2 + 1] *= 0.970
          orb.positions[pidx] += (Math.random() - 0.5) * 5
          orb.positions[pidx + 1] += (Math.random() - 0.5) * 5
        } else if (wh.phase === 'recovering' && exploded) {
          const dx = targetX - orb.positions[pidx], dy = targetY - orb.positions[pidx + 1]
          const dist = Math.sqrt(dx * dx + dy * dy) + 1
          const rt = Math.min(1, wh.recoverT)
          const pull = 0.015 + rt * rt * 0.10
          orb.velocities[i * 2] += (dx / dist) * pull * Math.min(dist, 100)
          orb.velocities[i * 2 + 1] += (dy / dist) * pull * Math.min(dist, 100)
          orb.velocities[i * 2] *= 0.88; orb.velocities[i * 2 + 1] *= 0.88
          orb.positions[pidx] += orb.velocities[i * 2]
          orb.positions[pidx + 1] += orb.velocities[i * 2 + 1]
          if (dist < 4) { orb.positions[pidx] = targetX; orb.positions[pidx + 1] = targetY; orb.velocities[i * 2] = 0; orb.velocities[i * 2 + 1] = 0 }
        } else {
          orb.positions[pidx] = targetX
          orb.positions[pidx + 1] = targetY
        }

        // Brownian at edges
        if (wh.phase === 'idle' || wh.phase === 'shrinking') {
          const edgeDist = Math.min(orb.positions[pidx], orb.positions[pidx + 1], W - orb.positions[pidx], H - orb.positions[pidx + 1])
          const edgeFrac = Math.max(0, 1 - edgeDist / 120)
          const bidx = i * 4
          if (edgeFrac > 0) {
            orb.brownian[bidx + 2] += (Math.random() - 0.5) * 3.0 * edgeFrac
            orb.brownian[bidx + 3] += (Math.random() - 0.5) * 3.0 * edgeFrac
            orb.brownian[bidx + 2] *= 0.88; orb.brownian[bidx + 3] *= 0.88
            orb.brownian[bidx] += orb.brownian[bidx + 2]; orb.brownian[bidx + 1] += orb.brownian[bidx + 3]
            orb.brownian[bidx] *= 0.92; orb.brownian[bidx + 1] *= 0.92
          } else { orb.brownian[bidx] *= 0.95; orb.brownian[bidx + 1] *= 0.95 }
        } else {
          orb.brownian[i * 4] *= 0.9; orb.brownian[i * 4 + 1] *= 0.9
        }

        const isRing = orb.props[i * 5 + 2] > 0.5
        drawList.push({
          x: orb.positions[pidx] + orb.brownian[i * 4],
          y: orb.positions[pidx + 1] + orb.brownian[i * 4 + 1],
          z: pr.pz, sz: orb.props[i * 5], br: orb.props[i * 5 + 1],
          trail: wh.phase === 'exploding' ? 0 : orb.props[i * 5 + 3],
          px: orb.positions[pidx + 2], py: orb.positions[pidx + 3],
          type: 'orb', isInner: false, isRing,
        })
      }

      // ── Core particles ──
      for (let i = 0; i < CORE_N; i++) {
        const nT = frame * core.noise[i * 3 + 1] * 0.016
        const nPh = core.noise[i * 3]
        const nAmp = core.noise[i * 3 + 2]
        const nx = Math.sin(nT + nPh) * nAmp
        const ny = Math.cos(nT * 1.3 + nPh * 2) * nAmp
        const nz = Math.sin(nT * 0.7 + nPh * 3) * nAmp

        const bx = core.basePositions[i * 3] + nx
        const by = core.basePositions[i * 3 + 1] + ny
        const bz = core.basePositions[i * 3 + 2] + nz

        const wx = bx * R, wy = by * R, wz = bz * R
        const pr = project3D(wx, wy, wz, wh.rotY, wh.rotX)
        const targetX = cx + pr.px, targetY = cy + pr.py

        if (wh.phase === 'exploding') {
          core.positions[i * 2] += core.velocities[i * 2]
          core.positions[i * 2 + 1] += core.velocities[i * 2 + 1]
          core.velocities[i * 2] *= 0.968; core.velocities[i * 2 + 1] *= 0.968
          core.positions[i * 2] += (Math.random() - 0.5) * 4
          core.positions[i * 2 + 1] += (Math.random() - 0.5) * 4
        } else if (wh.phase === 'recovering') {
          const dx = targetX - core.positions[i * 2], dy = targetY - core.positions[i * 2 + 1]
          const dist = Math.sqrt(dx * dx + dy * dy) + 1
          const rt = Math.min(1, wh.recoverT)
          const pull = 0.02 + rt * rt * 0.12
          core.velocities[i * 2] += (dx / dist) * pull * Math.min(dist, 80)
          core.velocities[i * 2 + 1] += (dy / dist) * pull * Math.min(dist, 80)
          core.velocities[i * 2] *= 0.90; core.velocities[i * 2 + 1] *= 0.90
          core.positions[i * 2] += core.velocities[i * 2]
          core.positions[i * 2 + 1] += core.velocities[i * 2 + 1]
          if (dist < 3) { core.positions[i * 2] = targetX; core.positions[i * 2 + 1] = targetY; core.velocities[i * 2] = 0; core.velocities[i * 2 + 1] = 0 }
        } else {
          core.positions[i * 2] = targetX
          core.positions[i * 2 + 1] = targetY
        }

        const depthBr = 0.5 + 0.5 * Math.max(0, pr.pz / (R || 1))
        const isInner = core.props[i * 4 + 3] > 0.5
        drawList.push({
          x: core.positions[i * 2], y: core.positions[i * 2 + 1], z: pr.pz,
          sz: core.props[i * 4] * (0.6 + 0.4 * B), br: core.props[i * 4 + 1] * depthBr,
          trail: 0, px: 0, py: 0, type: 'core', isInner, isRing: false,
        })
      }

      // ── Depth sort ──
      drawList.sort((a, b) => a.z - b.z)

      // ══════════════════════════════
      //  RENDER PARTICLES
      // ══════════════════════════════
      for (const d of drawList) {
        const depthScale = 0.7 + 0.3 * ((d.z + R * 4) / (R * 8))
        const rScale = (wh.phase === 'exploding' || wh.phase === 'recovering') ? 1.0 : (R / wh.baseR)
        const sz = d.sz * depthScale * Math.max(0.5, rScale)
        const alpha = Math.min(1, d.br * B * 1.8)
        if (alpha < 0.005 || sz < 0.1) continue

        if (d.type === 'core') {
          let rr: number, gg: number, bb: number
          if (d.isInner) {
            rr = Math.round(240 + d.br * 15); gg = Math.round(235 + d.br * 15); bb = Math.round(220 + d.br * 20)
          } else {
            rr = Math.round(235 + d.br * 20); gg = Math.round(200 + d.br * 40); bb = Math.round(140 + d.br * 40)
          }
          ctx.globalAlpha = alpha
          if (sz > 0.6) {
            ctx.fillStyle = `rgba(${rr},${gg},${bb},${alpha * 0.22})`
            ctx.beginPath(); ctx.arc(d.x, d.y, sz * 3.5, 0, Math.PI * 2); ctx.fill()
          }
          ctx.fillStyle = `rgba(${rr},${gg},${bb},${alpha})`
          ctx.beginPath(); ctx.arc(d.x, d.y, Math.max(0.3, sz), 0, Math.PI * 2); ctx.fill()
          if (d.br > 0.4 && sz > 0.5) {
            ctx.fillStyle = `rgba(255,255,250,${alpha * 0.5})`
            ctx.beginPath(); ctx.arc(d.x, d.y, sz * 0.45, 0, Math.PI * 2); ctx.fill()
          }
          ctx.globalAlpha = 1
        } else {
          let rr: number, gg: number, bb: number
          if (d.isRing) {
            rr = Math.round(245 + d.br * 10); gg = Math.round(225 + d.br * 25); bb = Math.round(180 + d.br * 40)
          } else {
            rr = Math.round(232 + d.br * 23); gg = Math.round(140 + d.br * 60); bb = Math.round(20 + d.br * 20)
          }
          ctx.globalAlpha = alpha
          if (d.trail > 0 && d.px && d.py) {
            const tdx = d.x - d.px, tdy = d.y - d.py
            const tLen = Math.sqrt(tdx * tdx + tdy * tdy)
            if (tLen > 1 && tLen < 60) {
              ctx.strokeStyle = `rgba(${rr},${gg},${bb},${alpha * d.trail * 0.3})`
              ctx.lineWidth = Math.max(0.3, sz * 0.5)
              ctx.beginPath()
              ctx.moveTo(d.px + (d.x - d.px) * 0.3, d.py + (d.y - d.py) * 0.3)
              ctx.lineTo(d.x, d.y); ctx.stroke()
            }
          }
          if (sz > 0.7) {
            ctx.fillStyle = `rgba(${rr},${gg},${bb},${alpha * 0.12})`
            ctx.beginPath(); ctx.arc(d.x, d.y, sz * 2.5, 0, Math.PI * 2); ctx.fill()
          }
          ctx.fillStyle = `rgba(${rr},${gg},${bb},${alpha})`
          ctx.beginPath(); ctx.arc(d.x, d.y, Math.max(0.3, sz), 0, Math.PI * 2); ctx.fill()
          ctx.globalAlpha = 1
        }
      }

      // ══════════════════════════════
      //  AMBIENT DUST
      // ══════════════════════════════
      for (let i = 0; i < DUST_N; i++) {
        const pidx = i * 2
        dust.props[i * 3 + 2] += 0.008
        dust.positions[pidx] += dust.velocities[pidx] + Math.sin(dust.props[i * 3 + 2]) * 0.0001
        dust.positions[pidx + 1] += dust.velocities[pidx + 1] + Math.cos(dust.props[i * 3 + 2] * 1.3) * 0.0001
        if (dust.positions[pidx] < -1.1) dust.positions[pidx] = 1.1
        if (dust.positions[pidx] > 1.1) dust.positions[pidx] = -1.1
        if (dust.positions[pidx + 1] < -1.1) dust.positions[pidx + 1] = 1.1
        if (dust.positions[pidx + 1] > 1.1) dust.positions[pidx + 1] = -1.1

        const sx = (dust.positions[pidx] * 0.5 + 0.5) * W
        const sy = (dust.positions[pidx + 1] * 0.5 + 0.5) * H
        if (mouse.x > 0) {
          const dx = sx - mouse.x, dy = sy - mouse.y
          const d = Math.sqrt(dx * dx + dy * dy)
          if (d < 200) {
            const f = (1 - d / 200) * 0.0005
            dust.positions[pidx] += (dx / d) * f
            dust.positions[pidx + 1] += (dy / d) * f
          }
        }

        const da = dust.props[i * 3 + 1] * B
        if (da < 0.005) continue
        ctx.fillStyle = `rgba(232,180,80,${da})`
        ctx.beginPath(); ctx.arc(sx, sy, dust.props[i * 3], 0, Math.PI * 2); ctx.fill()
        ctx.fillStyle = `rgba(232,180,80,${da * 0.2})`
        ctx.beginPath(); ctx.arc(sx, sy, dust.props[i * 3] * 3, 0, Math.PI * 2); ctx.fill()
      }

      // ══════════════════════════════
      //  LENSING RINGS
      // ══════════════════════════════
      if (B > 0.1 && wh.phase !== 'exploding') {
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(wh.rotY * 0.1)
        ctx.scale(1, 0.35 + Math.abs(Math.sin(wh.rotX)) * 0.15)
        const ringR = R * 1.15
        const ringGrad = ctx.createRadialGradient(0, 0, ringR * 0.92, 0, 0, ringR * 1.08)
        ringGrad.addColorStop(0, 'transparent')
        ringGrad.addColorStop(0.3, `rgba(255,220,140,${0.06 * B})`)
        ringGrad.addColorStop(0.5, `rgba(255,240,200,${0.12 * B})`)
        ringGrad.addColorStop(0.7, `rgba(255,220,140,${0.06 * B})`)
        ringGrad.addColorStop(1, 'transparent')
        ctx.fillStyle = ringGrad
        ctx.beginPath(); ctx.arc(0, 0, ringR * 1.1, 0, Math.PI * 2); ctx.fill()
        ctx.restore()

        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(wh.rotY * 0.15 + 0.3)
        ctx.scale(1, 0.25)
        const ring2R = R * 2.2
        const ring2Grad = ctx.createRadialGradient(0, 0, ring2R * 0.85, 0, 0, ring2R)
        ring2Grad.addColorStop(0, 'transparent')
        ring2Grad.addColorStop(0.4, `rgba(232,160,32,${0.03 * B})`)
        ring2Grad.addColorStop(0.6, `rgba(255,200,80,${0.06 * B})`)
        ring2Grad.addColorStop(0.8, `rgba(232,160,32,${0.03 * B})`)
        ring2Grad.addColorStop(1, 'transparent')
        ctx.fillStyle = ring2Grad
        ctx.beginPath(); ctx.arc(0, 0, ring2R, 0, Math.PI * 2); ctx.fill()
        ctx.restore()
      }

      rafRef.current = requestAnimationFrame(renderFrame)
    }

    resize()
    rafRef.current = requestAnimationFrame(renderFrame)
    window.addEventListener('resize', resize)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseleave', onMouseLeave)

    return () => {
      cancelAnimationFrame(rafRef.current)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseleave', onMouseLeave)
    }
  }, [whRef])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
    />
  )
}

// ══════════════════════════════
//  EXPORTED COMPONENT
// ══════════════════════════════
export const ParticleCanvas = forwardRef<WhiteHoleHandle>(function ParticleCanvas(_, ref) {
  const whRef = useRef<WHState>({
    baseR: 200,
    r: 200,
    tr: 200,
    bright: 0.30,
    tBright: 0.30,
    rotY: 0,
    rotX: 0.35,
    phase: 'idle',
    shrinkTimer: 0,
    explodeForce: 0,
    recoverT: 0,
  })

  useImperativeHandle(ref, () => ({
    triggerExplosion() {
      const wh = whRef.current
      if (wh.phase !== 'idle') return
      wh.phase = 'shrinking'
      wh.shrinkTimer = 22
      wh.tr = 22
      wh.tBright = 1.6
    },
  }))

  return <WhiteHoleCanvas whRef={whRef} />
})
