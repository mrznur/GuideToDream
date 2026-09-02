"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard, GraduationCap, KanbanSquare,
  MessageSquare, Search, Menu, X,
} from "lucide-react"
import { useState } from "react"

const links = [
  { href: "/dashboard",     label: "Dashboard",    icon: LayoutDashboard },
  { href: "/opportunities", label: "Opportunities", icon: GraduationCap   },
  { href: "/pipeline",      label: "Pipeline",      icon: KanbanSquare    },
  { href: "/assistant",     label: "Assistant",     icon: MessageSquare   },
  { href: "/research",      label: "Research",      icon: Search          },
]

export default function Navbar() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  return (
    <header style={{
      position: "sticky",
      top: 0,
      zIndex: 50,
      background: "var(--white)",
      borderBottom: "1px solid var(--border)",
      boxShadow: "0 1px 4px rgba(26,45,74,0.06)",
    }}>
      {/* ── Main bar ───────────────────────────────────────────────── */}
      <div style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "0 24px",
        height: "var(--nav-h)",
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}>

        {/* Logo — always visible */}
        <Link href="/" style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          textDecoration: "none",
          flexShrink: 0,
          marginRight: 8,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: "var(--navy)",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}>
            <GraduationCap style={{ width: 20, height: 20, color: "var(--gold-border)" }} />
          </div>
          <div className="hidden sm:block">
            <div style={{ fontSize: "1rem", fontWeight: 800, color: "var(--navy)", letterSpacing: "-0.02em", lineHeight: 1.1 }}>
              GuideToDream
            </div>
            <div style={{ fontSize: "0.58rem", color: "var(--gray-500)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              European Masters
            </div>
          </div>
          {/* Short name on very small screens */}
          <div className="sm:hidden" style={{ fontSize: "0.95rem", fontWeight: 800, color: "var(--navy)", letterSpacing: "-0.02em" }}>
            GTD
          </div>
        </Link>

        {/* ── Desktop nav links (hidden below md) ─────────────────── */}
        <nav className="hidden md:flex" style={{ alignItems: "center", gap: 2, flex: 1, justifyContent: "center" }}>
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/")
            return (
              <Link
                key={href}
                href={href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "8px 12px",
                  borderRadius: "var(--r-md)",
                  fontSize: "0.85rem",
                  fontWeight: active ? 600 : 500,
                  color: active ? "var(--navy)" : "var(--gray-600)",
                  textDecoration: "none",
                  background: active ? "var(--navy-faint)" : "transparent",
                  transition: "all 0.15s",
                  position: "relative",
                  whiteSpace: "nowrap",
                }}
                onMouseEnter={e => {
                  if (!active) {
                    (e.currentTarget as HTMLElement).style.background = "var(--gray-100)"
                    ;(e.currentTarget as HTMLElement).style.color = "var(--navy)"
                  }
                }}
                onMouseLeave={e => {
                  if (!active) {
                    (e.currentTarget as HTMLElement).style.background = "transparent"
                    ;(e.currentTarget as HTMLElement).style.color = "var(--gray-600)"
                  }
                }}
              >
                <Icon style={{ width: 14, height: 14 }} />
                {label}
                {/* Gold underline on active */}
                {active && (
                  <span style={{
                    position: "absolute",
                    bottom: -11,
                    left: 8,
                    right: 8,
                    height: 2,
                    background: "var(--gold)",
                    borderRadius: 2,
                  }} />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Spacer on desktop so hamburger is hidden + logo is left-aligned */}
        <div className="hidden md:block" style={{ flex: 1 }} />

        {/* ── Hamburger (hidden on md+, shown on mobile) ─────────── */}
        {/* Uses Tailwind classes only for flex — no inline display */}
        <button
          onClick={() => setOpen(v => !v)}
          className="flex items-center justify-center md:hidden"
          style={{
            width: 38,
            height: 38,
            borderRadius: "var(--r-md)",
            border: "1px solid var(--border)",
            background: "var(--white)",
            cursor: "pointer",
            color: "var(--gray-600)",
            flexShrink: 0,
          }}
          aria-label="Toggle menu"
        >
          {open ? <X style={{ width: 18, height: 18 }} /> : <Menu style={{ width: 18, height: 18 }} />}
        </button>
      </div>

      {/* ── Mobile dropdown (shown only when open) ───────────────── */}
      {open && (
        <div
          className="md:hidden"
          style={{
            borderTop: "1px solid var(--border)",
            background: "var(--white)",
            padding: "8px 16px 16px",
          }}
        >
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/")
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "11px 12px",
                  borderRadius: "var(--r-md)",
                  fontSize: "0.9rem",
                  fontWeight: active ? 600 : 400,
                  color: active ? "var(--navy)" : "var(--gray-700)",
                  textDecoration: "none",
                  background: active ? "var(--navy-faint)" : "transparent",
                  marginBottom: 2,
                  borderLeft: active ? `3px solid var(--gold)` : "3px solid transparent",
                }}
              >
                <Icon style={{ width: 17, height: 17, color: active ? "var(--gold)" : "var(--gray-400)" }} />
                {label}
              </Link>
            )
          })}
        </div>
      )}
    </header>
  )
}
