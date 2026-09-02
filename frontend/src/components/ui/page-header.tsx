import type { ReactNode } from "react"

interface PageHeaderProps {
  eyebrow?: string
  title: string
  subtitle?: string
  action?: ReactNode
  animClass?: string
}

export default function PageHeader({
  eyebrow, title, subtitle, action, animClass = "fade-up",
}: PageHeaderProps) {
  return (
    <div
      className={animClass}
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 16,
        marginBottom: 28,
        flexWrap: "wrap",
        paddingBottom: 22,
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div>
        {eyebrow && (
          <div style={{
            fontSize: "0.68rem",
            fontWeight: 700,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--gold)",
            marginBottom: 6,
          }}>
            {eyebrow}
          </div>
        )}
        <h1 style={{
          margin: 0,
          fontSize: "clamp(1.4rem, 2.5vw, 1.9rem)",
          fontWeight: 800,
          letterSpacing: "-0.025em",
          color: "var(--navy)",
          lineHeight: 1.1,
        }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{
            margin: "7px 0 0",
            fontSize: "0.9rem",
            color: "var(--gray-500)",
            lineHeight: 1.5,
          }}>
            {subtitle}
          </p>
        )}
      </div>
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
    </div>
  )
}
