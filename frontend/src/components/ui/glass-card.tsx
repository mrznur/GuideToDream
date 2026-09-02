/**
 * Card
 * ----
 * Clean white card with border and shadow.
 * Named GlassCard for backward compat but is now a plain card.
 */
import type { CSSProperties, ReactNode } from "react"

interface GlassCardProps {
  children: ReactNode
  style?: CSSProperties
  className?: string
  /** Coloured left border accent */
  accent?: string
  noPadding?: boolean
  elevated?: boolean
}

export default function GlassCard({
  children, style, className, accent, noPadding, elevated,
}: GlassCardProps) {
  return (
    <div
      className={className}
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        boxShadow: elevated ? "var(--shadow-md)" : "var(--shadow-sm)",
        padding: noPadding ? 0 : "20px 22px",
        position: "relative",
        overflow: "hidden",
        borderLeft: accent ? `3px solid ${accent}` : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  )
}
