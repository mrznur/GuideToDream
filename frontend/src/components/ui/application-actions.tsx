"use client"

import { useState } from "react"
import { api } from "@/lib/api"
import { CheckCircle, Bookmark, FileText, Send, Loader2 } from "lucide-react"

const ACTIONS = [
  { status: "shortlisted", label: "Shortlist",       icon: Bookmark,     style: "badge-blue"   },
  { status: "preparing",   label: "Start Preparing", icon: FileText,     style: "badge-purple" },
  { status: "applied",     label: "Mark Applied",    icon: Send,         style: "badge-amber"  },
  { status: "accepted",    label: "Accepted!",        icon: CheckCircle,  style: "badge-green"  },
]

const COLORS: Record<string, { bg: string; color: string; border: string }> = {
  "badge-blue":   { bg: "var(--blue-bg)",   color: "var(--blue)",   border: "var(--blue-border)"   },
  "badge-purple": { bg: "var(--purple-bg)", color: "var(--purple)", border: "var(--purple-border)" },
  "badge-amber":  { bg: "var(--amber-bg)",  color: "var(--amber)",  border: "var(--amber-border)"  },
  "badge-green":  { bg: "var(--green-bg)",  color: "var(--green)",  border: "var(--green-border)"  },
}

interface Props {
  opportunityId: string
  currentStatus: string | null
}

export default function ApplicationActions({ opportunityId, currentStatus }: Props) {
  const [status, setStatus]   = useState(currentStatus)
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError]     = useState("")

  async function handleAction(newStatus: string) {
    setLoading(newStatus); setError("")
    try {
      try { await api.createApplication(opportunityId) } catch { /* 409 = ok */ }
      const apps = await api.getApplications()
      const app  = apps.find(a => a.opportunity_id === opportunityId)
      if (!app) { setError("Application created. Refresh and try again."); setStatus("discovered"); return }
      if (app.status === newStatus) { setStatus(newStatus); return }
      const updated = await api.transitionStatus(app.id, newStatus)
      setStatus(updated.status)
    } catch (e: any) {
      const msg = e.message || ""
      setError(msg.includes("Invalid transition")
        ? `Can't jump to "${newStatus}" from "${status}" — follow the pipeline order.`
        : msg || "Failed to update status")
    } finally { setLoading(null) }
  }

  return (
    <div style={{
      background: "var(--bg-card)", border: "1px solid var(--border)",
      borderRadius: "var(--r-lg)", padding: "20px 22px", boxShadow: "var(--shadow-sm)",
    }}>
      <h2 style={{ margin: "0 0 4px", fontSize: "0.9rem", fontWeight: 700, color: "var(--navy)" }}>
        Application Tracker
      </h2>
      {status && status !== "discovered" ? (
        <p style={{ margin: "0 0 16px", fontSize: "0.82rem", color: "var(--gray-500)" }}>
          Current status: <strong style={{ color: "var(--navy)", textTransform: "capitalize" }}>{status.replace(/_/g, " ")}</strong>
        </p>
      ) : (
        <p style={{ margin: "0 0 16px", fontSize: "0.82rem", color: "var(--gray-500)" }}>
          Not yet tracked — add to your pipeline:
        </p>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {ACTIONS.map(({ status: s, label, icon: Icon, style }) => {
          const isCurrent = status === s
          const colors    = COLORS[style]
          return (
            <button key={s} onClick={() => handleAction(s)}
              disabled={!!loading || isCurrent}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "8px 16px", borderRadius: "var(--r-md)",
                fontSize: "0.82rem", fontWeight: 600,
                background: isCurrent ? colors.bg : "var(--white)",
                color: isCurrent ? colors.color : "var(--gray-600)",
                border: `1px solid ${isCurrent ? colors.border : "var(--border)"}`,
                cursor: loading || isCurrent ? "not-allowed" : "pointer",
                opacity: loading && loading !== s ? 0.5 : 1,
                transition: "all 0.12s",
              }}
              onMouseEnter={e => {
                if (!loading && !isCurrent) {
                  (e.currentTarget as HTMLElement).style.background = colors.bg
                  ;(e.currentTarget as HTMLElement).style.color = colors.color
                  ;(e.currentTarget as HTMLElement).style.borderColor = colors.border
                }
              }}
              onMouseLeave={e => {
                if (!loading && !isCurrent) {
                  (e.currentTarget as HTMLElement).style.background = "var(--white)"
                  ;(e.currentTarget as HTMLElement).style.color = "var(--gray-600)"
                  ;(e.currentTarget as HTMLElement).style.borderColor = "var(--border)"
                }
              }}
            >
              {loading === s
                ? <Loader2 style={{ width: 13, height: 13 }} className="animate-spin" />
                : <Icon    style={{ width: 13, height: 13 }} />}
              {isCurrent ? `✓ ${label}` : label}
            </button>
          )
        })}
      </div>

      {error && (
        <div style={{
          marginTop: 10, padding: "7px 11px", borderRadius: "var(--r-sm)",
          background: "var(--red-bg)", border: "1px solid var(--red-border)",
          color: "var(--red)", fontSize: "0.78rem",
        }}>
          {error}
        </div>
      )}
    </div>
  )
}
