"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

// Simple, elegant hero — fades in, waits 3 seconds, then navigates to dashboard.
// No scroll mechanics. Clean and instant.

export default function AnimatedHero() {
  const router = useRouter()
  const [phase, setPhase] = useState<"entering" | "visible" | "exiting">("entering")

  useEffect(() => {
    // Phase 1: fade in (0.8s)
    const t1 = setTimeout(() => setPhase("visible"), 800)
    // Phase 2: show for 2.5s, then start exit
    const t2 = setTimeout(() => setPhase("exiting"), 3500)
    // Phase 3: navigate after exit animation (0.6s)
    const t3 = setTimeout(() => router.push("/dashboard"), 4100)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
    }
  }, [router])

  const opacity =
    phase === "entering" ? 0 : phase === "visible" ? 1 : 0

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        background: "#05070d",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        opacity,
        transition:
          phase === "entering"
            ? "opacity 0.8s ease"
            : "opacity 0.6s ease",
      }}
    >
      {/* Logo mark */}
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 16,
          background: "linear-gradient(135deg, #3b82f6, #6366f1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 0 40px rgba(99,102,241,0.4)",
        }}
      >
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
          <path d="M6 12v5c3 3 9 3 12 0v-5" />
        </svg>
      </div>

      {/* Title */}
      <div style={{ textAlign: "center" }}>
        <h1
          style={{
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            fontWeight: 700,
            fontSize: "clamp(26px, 4vw, 48px)",
            letterSpacing: "-0.02em",
            color: "#f2f4f8",
            margin: "0 0 8px",
            lineHeight: 1.1,
          }}
        >
          GuideToDream
        </h1>
        <p
          style={{
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            fontSize: "clamp(13px, 1.5vw, 16px)",
            color: "rgba(180,200,230,0.6)",
            letterSpacing: "0.05em",
            margin: 0,
          }}
        >
          European Masters & Scholarship Intelligence
        </p>
      </div>

      {/* Loading dots */}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "rgba(99,179,237,0.6)",
              animation: `dot-pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </div>

      <style>{`
        @keyframes dot-pulse {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1.2); }
        }
      `}</style>
    </div>
  )
}
