"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

export default function AnimatedHero() {
  const router = useRouter()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setVisible(true), 60)
    const t2 = setTimeout(() => router.push("/dashboard"), 3200)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [router])

  return (
    <div style={{
      minHeight: "100dvh",
      background: "linear-gradient(160deg, #f0f5ff 0%, #fdfbf7 60%, #fff 100%)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "40px 24px",
      position: "relative",
      overflow: "hidden",
    }}>

      {/* Decorative circles */}
      <div style={{
        position: "absolute", top: -120, right: -120,
        width: 400, height: 400, borderRadius: "50%",
        background: "rgba(26,45,74,0.04)",
        pointerEvents: "none",
      }} />
      <div style={{
        position: "absolute", bottom: -80, left: -80,
        width: 300, height: 300, borderRadius: "50%",
        background: "rgba(200,146,42,0.05)",
        pointerEvents: "none",
      }} />

      {/* Content */}
      <div style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(18px)",
        transition: "opacity 0.9s ease, transform 0.9s cubic-bezier(0.22,1,0.36,1)",
        textAlign: "center",
        maxWidth: 520,
        position: "relative",
        zIndex: 1,
      }}>

        {/* Icon mark */}
        <div style={{
          width: 72,
          height: 72,
          borderRadius: 18,
          background: "var(--navy)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto 28px",
          boxShadow: "0 8px 24px rgba(26,45,74,0.22)",
        }}>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none"
            stroke="#f0c875" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
            <path d="M6 12v5c3 3 9 3 12 0v-5" />
          </svg>
        </div>

        <h1 style={{
          fontSize: "clamp(2rem, 5vw, 3rem)",
          fontWeight: 900,
          color: "var(--navy)",
          letterSpacing: "-0.03em",
          lineHeight: 1.05,
          marginBottom: 14,
        }}>
          GuideToDream
        </h1>

        <p style={{
          fontSize: "1.05rem",
          color: "var(--gray-600)",
          lineHeight: 1.6,
          marginBottom: 32,
        }}>
          Find your European Master's. Track applications. Own the process.
        </p>

        {/* Loading indicator */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          color: "var(--gray-400)",
          fontSize: "0.82rem",
        }}>
          {[0, 1, 2].map(i => (
            <span key={i} style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--navy)",
              opacity: 0.4,
              display: "block",
              animation: `dot-pulse 1.3s ease-in-out ${i * 0.2}s infinite`,
            }} />
          ))}
          <span>Loading your dashboard</span>
        </div>
      </div>
    </div>
  )
}
