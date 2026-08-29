"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  GraduationCap,
  KanbanSquare,
  MessageSquare,
  Search,
  Menu,
  X,
} from "lucide-react"
import { useState } from "react"

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/opportunities", label: "Opportunities", icon: GraduationCap },
  { href: "/pipeline", label: "Pipeline", icon: KanbanSquare },
  { href: "/assistant", label: "Assistant", icon: MessageSquare },
  { href: "/research", label: "Research", icon: Search },
]

export default function Navbar() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  return (
    <nav className="fixed top-0 left-0 right-0 z-50"
      style={{
        background: "rgba(5,7,13,0.75)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}>
            <GraduationCap className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-sm tracking-tight"
            style={{ background: "linear-gradient(135deg, #63b3ed, #818cf8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            GuideToDream
          </span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-0.5">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href
            return (
              <Link key={href} href={href}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200",
                  active
                    ? "text-white bg-white/8"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                )}
                style={active ? { background: "rgba(99,179,237,0.1)", color: "#93c5fd" } : {}}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </Link>
            )
          })}
        </div>

        {/* Mobile button */}
        <button className="md:hidden text-slate-400 hover:text-white transition-colors"
          onClick={() => setOpen(!open)}>
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden px-4 pb-3 pt-1 flex flex-col gap-0.5"
          style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          {links.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                pathname === href ? "text-blue-300 bg-blue-500/10" : "text-slate-400 hover:text-white hover:bg-white/5"
              )}>
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  )
}
