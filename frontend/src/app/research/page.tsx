"use client"

import { useState, useEffect } from "react"
import PageShell from "@/components/layout/page-shell"
import PageHeader from "@/components/ui/page-header"
import GlassCard from "@/components/ui/glass-card"
import { api, type ResearchRun } from "@/lib/api"
import { Play, CheckCircle2, AlertCircle, Clock, Loader2, TrendingUp, Zap, Search } from "lucide-react"
import { timeAgo } from "@/lib/utils"

const RUN_STATUS: Record<string, { badgeClass: string; icon: React.ElementType }> = {
  completed: { badgeClass: "badge-green",  icon: CheckCircle2 },
  partial:   { badgeClass: "badge-amber",  icon: AlertCircle  },
  running:   { badgeClass: "badge-blue",   icon: Loader2      },
  failed:    { badgeClass: "badge-red",    icon: AlertCircle  },
}

function RunRow({ run }: { run: ResearchRun }) {
  const cfg = RUN_STATUS[run.status] ?? RUN_STATUS.failed
  const Icon = cfg.icon

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 14,
      padding: "13px 18px", borderBottom: "1px solid var(--border)",
    }}>
      <div style={{
        width: 34, height: 34, borderRadius: "var(--r-md)", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "var(--gray-100)", border: "1px solid var(--border)",
      }}>
        <Icon style={{ width: 14, height: 14, color: "var(--gray-500)" }}
          className={run.status === "running" ? "animate-spin" : ""} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--navy)", marginBottom: 3 }}>
          {new Date(run.started_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
          {run.completed_at && (
            <span style={{ color: "var(--gray-400)", fontWeight: 400, marginLeft: 6, fontSize: "0.78rem" }}>
              · {timeAgo(run.started_at)}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {[
            { v: run.queries_generated, l: "queries" },
            { v: run.pages_fetched,     l: "pages"   },
            { v: run.llm_calls,         l: "LLM"     },
            { v: run.duration_seconds ? `${run.duration_seconds}s` : null, l: "time" },
          ].filter(x => x.v !== null && x.v !== 0).map(({ v, l }) => (
            <span key={l} style={{ fontSize: "0.72rem", color: "var(--gray-400)" }}>
              <strong style={{ color: "var(--gray-600)" }}>{v}</strong> {l}
            </span>
          ))}
        </div>
        {run.errors?.length > 0 && (
          <p style={{ margin: "3px 0 0", fontSize: "0.7rem", color: "var(--red)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            [{run.errors[0].stage}] {run.errors[0].error}
          </p>
        )}
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
        {run.opportunities_found > 0 && (
          <span className="badge badge-green">+{run.opportunities_found}</span>
        )}
        <span className={`badge ${cfg.badgeClass}`}>{run.status}</span>
      </div>
    </div>
  )
}

export default function ResearchPage() {
  const [runs, setRuns]                   = useState<ResearchRun[]>([])
  const [loading, setLoading]             = useState(true)
  const [triggering, setTriggering]       = useState(false)
  const [msg, setMsg]                     = useState<{ text: string; ok: boolean } | null>(null)
  const [scheduleStatus, setScheduleStatus] = useState<any>(null)

  useEffect(() => {
    Promise.all([
      api.getRuns(20).then(setRuns).catch(() => {}),
      api.getScheduleStatus().then(setScheduleStatus).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  async function trigger() {
    setTriggering(true); setMsg(null)
    try {
      await api.triggerResearch()
      setMsg({ text: "Research cycle triggered. Check back in a few minutes.", ok: true })
      setTimeout(() => api.getRuns(20).then(setRuns).catch(() => {}), 6000)
    } catch {
      setMsg({ text: "Failed to trigger — is the API running?", ok: false })
    } finally { setTriggering(false) }
  }

  const completedRuns = runs.filter(r => r.status === "completed")
  const totalFound    = runs.reduce((s, r) => s + r.opportunities_found, 0)
  const totalPages    = runs.reduce((s, r) => s + r.pages_fetched, 0)

  return (
    <PageShell maxWidth={860}>
      <PageHeader
        eyebrow="Discovery"
        title="Research"
        subtitle="Automated search across European universities — extracts, scores, and tracks every programme"
      />

      {/* Trigger card */}
      <GlassCard elevated className="fade-up-1" style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", gap: 20, alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 240 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div style={{
                width: 38, height: 38, borderRadius: "var(--r-md)",
                background: "var(--navy)", display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Search style={{ width: 18, height: 18, color: "var(--gold-border)" }} />
              </div>
              <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 700, color: "var(--navy)" }}>
                Run Research Cycle
              </h2>
            </div>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--gray-500)", lineHeight: 1.6, maxWidth: 400 }}>
              Searches European universities, fetches official pages, extracts data with Gemini,
              and scores everything against your profile. Runs automatically at 08:00 daily.
            </p>
            {msg && (
              <div style={{
                marginTop: 12, display: "flex", alignItems: "center", gap: 8,
                fontSize: "0.82rem", padding: "8px 12px", borderRadius: "var(--r-md)",
                color: msg.ok ? "var(--green)" : "var(--red)",
                background: msg.ok ? "var(--green-bg)" : "var(--red-bg)",
                border: `1px solid ${msg.ok ? "var(--green-border)" : "var(--red-border)"}`,
              }}>
                {msg.ok ? <CheckCircle2 style={{ width: 13, height: 13 }} /> : <AlertCircle style={{ width: 13, height: 13 }} />}
                {msg.text}
              </div>
            )}
          </div>
          <button onClick={trigger} disabled={triggering} className="btn-primary" style={{ flexShrink: 0 }}>
            {triggering
              ? <><Loader2 style={{ width: 14, height: 14 }} className="animate-spin" /> Running…</>
              : <><Play style={{ width: 14, height: 14 }} /> Run Now</>}
          </button>
        </div>
      </GlassCard>

      {/* Schedule */}
      {scheduleStatus && (
        <GlassCard className="fade-up-2" style={{ marginBottom: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <Clock style={{ width: 14, height: 14, color: "var(--blue)" }} />
              <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--navy)" }}>Automated Schedule</span>
            </div>
            <span className={`badge ${scheduleStatus.running ? "badge-green" : "badge-red"}`}>
              {scheduleStatus.running ? "● Active" : "● Stopped"}
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {(scheduleStatus.jobs ?? []).map((job: any) => (
              <div key={job.id} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "7px 10px", background: "var(--gray-50)", borderRadius: "var(--r-sm)", border: "1px solid var(--border)",
              }}>
                <span style={{ fontSize: "0.82rem", color: "var(--gray-700)", fontWeight: 500 }}>{job.name}</span>
                <span style={{ fontSize: "0.75rem", color: "var(--gray-400)" }}>
                  {job.next_run ? new Date(job.next_run).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "—"}
                </span>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Run history */}
      <GlassCard className="fade-up-3" noPadding>
        <div style={{
          padding: "14px 18px", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "var(--gray-50)", borderRadius: "var(--r-lg) var(--r-lg) 0 0",
          flexWrap: "wrap", gap: 12,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <TrendingUp style={{ width: 14, height: 14, color: "var(--navy)" }} />
            <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--navy)" }}>Run History</span>
          </div>
          {!loading && runs.length > 0 && (
            <div style={{ display: "flex", gap: 18 }}>
              {[
                { v: completedRuns.length, l: "completed" },
                { v: totalFound,           l: "found"     },
                { v: totalPages,           l: "pages"     },
              ].map(({ v, l }) => (
                <div key={l} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--navy)", lineHeight: 1 }}>{v}</div>
                  <div style={{ fontSize: "0.62rem", color: "var(--gray-400)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>{l}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {loading ? (
          <div style={{ padding: "16px 18px", display: "flex", flexDirection: "column", gap: 8 }}>
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton" style={{ height: 60 }} />)}
          </div>
        ) : runs.length === 0 ? (
          <div style={{ padding: "48px 24px", textAlign: "center" }}>
            <Zap style={{ width: 32, height: 32, color: "var(--gray-300)", margin: "0 auto 12px" }} />
            <p style={{ margin: 0, color: "var(--gray-500)" }}>No research runs yet. Hit Run Now to start.</p>
          </div>
        ) : runs.map(run => <RunRow key={run.id} run={run} />)}
      </GlassCard>
    </PageShell>
  )
}
