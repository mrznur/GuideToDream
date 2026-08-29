"use client"

import { useEffect, useRef, useState } from "react"

// ─────────────────────────────────────────────────────────────
// ANIMATED HERO — scroll-scrub canvas background
// No external assets. Particles + city skyline effect.
// Scroll drives progress 0→1:
//   0.0 → dark night sky, stars visible, title prominent
//   0.5 → city lights rise from bottom, stars fade
//   1.0 → full city glow, tagline appears
// ─────────────────────────────────────────────────────────────

interface Particle {
  x: number
  y: number
  size: number
  speed: number
  opacity: number
  twinkle: number
}

export interface AnimatedHeroProps {
  title?: string
  tagline?: string
  subtitle?: string
  scrollHint?: string
  scrubDistance?: number
  onComplete?: () => void
}

export default function AnimatedHero({
  title = "BEGIN YOUR DREAM JOURNEY",
  tagline = "Every door to your future is already open.",
  subtitle = "AI-powered European Masters & Scholarship Intelligence",
  scrollHint = "SCROLL",
  scrubDistance = 2400,
}: AnimatedHeroProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const progressRef = useRef(0)
  const targetRef = useRef(0)
  const rafRef = useRef(0)
  const particlesRef = useRef<Particle[]>([])
  const [progress, setProgress] = useState(0)
  const [hasScrolled, setHasScrolled] = useState(false)

  // Init particles
  useEffect(() => {
    const count = 180
    const pts: Particle[] = []
    for (let i = 0; i < count; i++) {
      pts.push({
        x: Math.random(),
        y: Math.random() * 0.75,
        size: Math.random() * 1.8 + 0.4,
        speed: Math.random() * 0.0002 + 0.00005,
        opacity: Math.random() * 0.8 + 0.2,
        twinkle: Math.random() * Math.PI * 2,
      })
    }
    particlesRef.current = pts
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let locked = false
    let lockedScrollY = 0
    let touchStartY = 0

    function resize() {
      if (!canvas) return
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener("resize", resize)

    // ── Lock body scroll ──
    function engageLock() {
      if (locked) return
      locked = true
      lockedScrollY = window.scrollY
      document.body.style.position = "fixed"
      document.body.style.top = `-${lockedScrollY}px`
      document.body.style.left = "0"
      document.body.style.right = "0"
      document.body.style.width = "100%"
    }

    function releaseLock() {
      if (!locked) return
      locked = false
      const y = lockedScrollY
      document.body.style.position = ""
      document.body.style.top = ""
      document.body.style.left = ""
      document.body.style.right = ""
      document.body.style.width = ""
      window.scrollTo(0, y)
    }

    engageLock()

    function addDelta(dy: number) {
      const next = Math.min(1, Math.max(0, targetRef.current + dy / scrubDistance))
      targetRef.current = next
      if (next > 0.01) setHasScrolled(true)
    }

    const onWheel = (e: WheelEvent) => {
      addDelta(e.deltaY)
      e.preventDefault()
    }
    const onTouchStart = (e: TouchEvent) => {
      touchStartY = e.touches[0]?.clientY ?? 0
    }
    const onTouchMove = (e: TouchEvent) => {
      const y = e.touches[0]?.clientY ?? touchStartY
      addDelta(touchStartY - y)
      touchStartY = y
      e.preventDefault()
    }

    window.addEventListener("wheel", onWheel, { passive: false })
    window.addEventListener("touchstart", onTouchStart, { passive: true })
    window.addEventListener("touchmove", onTouchMove, { passive: false })

    // ── Draw ──
    function drawFrame(t: number) {
      if (!canvas || !ctx) return

      const p = progressRef.current
      const W = canvas.width
      const H = canvas.height

      // Background gradient — transitions from deep navy to warm city glow
      const sky = ctx.createLinearGradient(0, 0, 0, H)
      const r1 = Math.round(5 + p * 15)
      const g1 = Math.round(7 + p * 10)
      const b1 = Math.round(13 + p * 8)
      const r2 = Math.round(8 + p * 30)
      const g2 = Math.round(12 + p * 18)
      const b2 = Math.round(20 + p * 5)
      sky.addColorStop(0, `rgb(${r1},${g1},${b1})`)
      sky.addColorStop(1, `rgb(${r2},${g2},${b2})`)
      ctx.fillStyle = sky
      ctx.fillRect(0, 0, W, H)

      // Stars — fade out as city rises
      const starAlpha = Math.max(0, 1 - p * 1.8)
      particlesRef.current.forEach((star) => {
        star.twinkle += 0.02
        const twinkle = 0.6 + 0.4 * Math.sin(star.twinkle)
        const alpha = star.opacity * twinkle * starAlpha
        if (alpha < 0.01) return
        ctx.beginPath()
        ctx.arc(star.x * W, star.y * H, star.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(220,230,255,${alpha.toFixed(2)})`
        ctx.fill()
      })

      // City skyline — rises up from bottom as progress increases
      const cityRise = Math.max(0, (p - 0.2) / 0.8)
      if (cityRise > 0) {
        const baseY = H * (1 - cityRise * 0.35)

        // Buildings
        const buildings = [
          { x: 0.05, w: 0.06, h: 0.18 },
          { x: 0.12, w: 0.04, h: 0.25 },
          { x: 0.17, w: 0.07, h: 0.15 },
          { x: 0.25, w: 0.05, h: 0.30 },
          { x: 0.31, w: 0.08, h: 0.22 },
          { x: 0.40, w: 0.06, h: 0.35 },
          { x: 0.47, w: 0.04, h: 0.28 },
          { x: 0.52, w: 0.09, h: 0.38 },
          { x: 0.62, w: 0.05, h: 0.25 },
          { x: 0.68, w: 0.07, h: 0.20 },
          { x: 0.76, w: 0.04, h: 0.30 },
          { x: 0.81, w: 0.08, h: 0.18 },
          { x: 0.90, w: 0.05, h: 0.24 },
          { x: 0.96, w: 0.06, h: 0.15 },
        ]

        buildings.forEach(({ x, w, h }) => {
          const bH = H * h * cityRise
          const bX = x * W
          const bW = w * W
          const bY = baseY - bH

          // Building body
          const bGrad = ctx.createLinearGradient(bX, bY, bX + bW, bY)
          bGrad.addColorStop(0, `rgba(15,20,35,${0.9 * cityRise})`)
          bGrad.addColorStop(1, `rgba(20,28,45,${0.85 * cityRise})`)
          ctx.fillStyle = bGrad
          ctx.fillRect(bX, bY, bW, bH)

          // Windows — random lit squares
          const rows = Math.floor(bH / 14)
          const cols = Math.floor(bW / 10)
          for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
              const seed = Math.sin((x + w) * 100 + r * 13 + c * 7) * 0.5 + 0.5
              if (seed > 0.55) continue
              const wx = bX + c * 10 + 3
              const wy = bY + r * 14 + 4
              const warmth = seed > 0.3 ? "255,220,120" : "180,210,255"
              ctx.fillStyle = `rgba(${warmth},${(0.4 + seed * 0.5) * cityRise})`
              ctx.fillRect(wx, wy, 5, 7)
            }
          }
        })

        // Ground glow
        const gGrad = ctx.createLinearGradient(0, baseY - 20, 0, H)
        gGrad.addColorStop(0, `rgba(255,160,60,${0.12 * cityRise})`)
        gGrad.addColorStop(0.5, `rgba(255,120,40,${0.06 * cityRise})`)
        gGrad.addColorStop(1, `rgba(0,0,0,0)`)
        ctx.fillStyle = gGrad
        ctx.fillRect(0, baseY - 20, W, H - baseY + 20)
      }

      // Subtle aurora effect at top — fades in mid-scroll
      const auroraAlpha = Math.max(0, Math.min(1, (p - 0.3) / 0.4)) * 0.08
      if (auroraAlpha > 0) {
        const aGrad = ctx.createRadialGradient(W * 0.5, 0, 0, W * 0.5, 0, W * 0.6)
        aGrad.addColorStop(0, `rgba(99,179,237,${auroraAlpha})`)
        aGrad.addColorStop(1, "rgba(0,0,0,0)")
        ctx.fillStyle = aGrad
        ctx.fillRect(0, 0, W, H * 0.4)
      }

      rafRef.current = requestAnimationFrame(drawFrame)
    }

    // Animation loop — lerp progress
    let lastT = 0
    function tick(t: number) {
      const dt = Math.min(t - lastT, 50)
      lastT = t
      const lerp = 1 - Math.pow(0.85, dt / 16)
      progressRef.current += (targetRef.current - progressRef.current) * lerp
      setProgress(Math.round(progressRef.current * 100) / 100)
      drawFrame(t)
    }

    rafRef.current = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(rafRef.current)
      window.removeEventListener("resize", resize)
      window.removeEventListener("wheel", onWheel)
      window.removeEventListener("touchstart", onTouchStart)
      window.removeEventListener("touchmove", onTouchMove)
      releaseLock()
    }
  }, [scrubDistance])

  const titleOpacity = Math.max(0, 1 - progress / 0.35)
  const taglineOpacity = Math.max(0, (progress - 0.82) / 0.18)

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", height: "100dvh", width: "100%", overflow: "hidden" }}
    >
      <canvas
        ref={canvasRef}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      />

      {/* Title */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "0 6%",
          gap: 16,
          opacity: titleOpacity,
          transform: `translateY(${(1 - titleOpacity) * -20}px)`,
          transition: "none",
          pointerEvents: "none",
        }}
      >
        <h1
          style={{
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            fontWeight: 800,
            fontSize: "clamp(28px, 6vw, 82px)",
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
            color: "#f2f4f8",
            textShadow: "0 4px 40px rgba(0,0,0,0.8)",
            margin: 0,
          }}
        >
          {title}
        </h1>
        <p
          style={{
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            fontSize: "clamp(12px, 1.6vw, 18px)",
            color: "rgba(180,200,230,0.7)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            margin: 0,
          }}
        >
          {subtitle}
        </p>
      </div>

      {/* Tagline (end of scroll) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 8%",
          textAlign: "center",
          opacity: taglineOpacity,
          transform: `translateY(${(1 - taglineOpacity) * 20}px)`,
          pointerEvents: "none",
        }}
      >
        <p
          style={{
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            fontWeight: 700,
            fontSize: "clamp(20px, 3.4vw, 42px)",
            lineHeight: 1.2,
            color: "#f2f4f8",
            textShadow: "0 4px 30px rgba(0,0,0,0.6)",
            margin: 0,
          }}
        >
          {tagline}
        </p>
      </div>

      {/* Scroll hint */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          bottom: "clamp(20px, 6vh, 48px)",
          transform: "translateX(-50%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
          color: "rgba(180,210,255,0.6)",
          fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif",
          fontSize: "clamp(10px, 1.3vw, 12px)",
          fontWeight: 600,
          letterSpacing: "0.3em",
          opacity: hasScrolled ? 0 : 1,
          transition: "opacity 0.4s ease",
          pointerEvents: "none",
        }}
      >
        <span>{scrollHint}</span>
        <svg width="14" height="18" viewBox="0 0 14 18">
          <style>{`@keyframes bounce-hint{0%,100%{transform:translateY(0);opacity:.5}50%{transform:translateY(5px);opacity:1}}.bh{animation:bounce-hint 1.6s ease-in-out infinite}`}</style>
          <path className="bh" d="M7 1 L7 17 M2 12 L7 17 L12 12" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      {/* Progress bar */}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 2, background: "rgba(255,255,255,0.06)" }}>
        <div
          style={{
            height: "100%",
            width: `${progress * 100}%`,
            background: "linear-gradient(90deg, rgba(99,179,237,0.5), rgba(99,179,237,0.9))",
            transition: "none",
          }}
        />
      </div>
    </div>
  )
}
