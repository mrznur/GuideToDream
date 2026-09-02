"use client"

import { useState, useEffect } from "react"
import PageShell from "@/components/layout/page-shell"
import PageHeader from "@/components/ui/page-header"
import GlassCard from "@/components/ui/glass-card"
import { api, type ResearchRun } from "@/lib/api"
import {
  Play, CheckCircle2, AlertCircle, Clock, Loader2,
  TrendingUp, Zap, Search, Globe, X, Plus, Save,
} from "lucide-react"
import { timeAgo } from "@/lib/utils"

// ─── Run status config ────────────────────────────────────────────────────
const RUN_STATUS: Record<string, { badgeClass: string; icon: React.ElementType }> = {
  completed: { badgeClass: "badge-green", icon: CheckCircle2 },
  partial:   { badgeClass: "badge-amber", icon: AlertCircle  },
  running:   { badgeClass: "badge-blue",  icon: Loader2      },
  failed:    { badgeClass: "badge-red",   icon: AlertCircle  },
}

// ─── Run row ──────────────────────────────────────────────────────────────
function RunRow({ run }: { run: ResearchRun }) {
  const cfg  = RUN_STATUS[run.status] ?? RUN_STATUS.failed
  const Icon = cfg.icon
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "13px 18px", borderBottom: "1px solid var(--border)" }}>
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

// ─── Country manager ──────────────────────────────────────────────────────
function CountryManager() {
  const [preferred, setPreferred] = useState<string[]>([])
  const [avoided, setAvoid]       = useState<string[]>([])
  const [newCountry, setNew]       = useState("")
  const [tab, setTab]              = useState<"preferred" | "avoided">("preferred")
  const [saving, setSaving]        = useState(false)
  const [saved, setSaved]          = useState(false)
  const [loadError, setLoadError]  = useState(false)

  useEffect(() => {
    api.getPreferences()
      .then(p => {
        setPreferred(p.preferred_countries)
        setAvoid(p.avoided_countries)
      })
      .catch(() => setLoadError(true))
  }, [])

  function remove(country: string, list: "preferred" | "avoided") {
    if (list === "preferred") setPreferred(p => p.filter(c => c !== country))
    else setAvoid(p => p.filter(c => c !== country))
  }

  function add() {
    const val = newCountry.trim()
    if (!val) return
    const title = val.charAt(0).toUpperCase() + val.slice(1)
    if (tab === "preferred" && !preferred.includes(title)) setPreferred(p => [...p, title])
    if (tab === "avoided"   && !avoided.includes(title))   setAvoid(p => [...p, title])
    setNew("")
  }

  async function save() {
    setSaving(true)
    try {
      const updated = await api.updateCountries(preferred, avoided)
      setPreferred(updated.preferred_countries)
      setAvoid(updated.avoided_countries)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch { /* ignore */ }
    finally { setSaving(false) }
  }

  const activeList = tab === "preferred" ? preferred : avoided
  const tabColor   = tab === "preferred" ? "var(--blue)" : "var(--red)"

  return (
    <GlassCard className="fade-up-2" style={{ marginBottom: 18 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <Globe style={{ width: 16, height: 16, color: "var(--navy)" }} />
        <span style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--navy)" }}>
          Search Countries
        </span>
        <span style={{ marginLeft: "auto", fontSize: "0.78rem", color: "var(--gray-400)" }}>
          Controls which countries the research cycle targets
        </span>
      </div>

      {loadError ? (
        <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--red)" }}>
          Couldn't load preferences — is the backend running?
        </p>
      ) : (
        <>
          {/* Tab switcher */}
          <div style={{ display: "flex", gap: 4, marginBottom: 14, padding: "4px", background: "var(--gray-100)", borderRadius: "var(--r-md)", width: "fit-content" }}>
            {(["preferred", "avoided"] as const).map(t => (
              <button key={t} onClick={() => setTab(t)} style={{
                padding: "5px 16px", borderRadius: "var(--r-sm)", fontSize: "0.8rem", fontWeight: 600,
                border: "none", cursor: "pointer", transition: "all 0.12s",
                background: tab === t ? "var(--white)" : "transparent",
                color: tab === t ? "var(--navy)" : "var(--gray-500)",
                boxShadow: tab === t ? "var(--shadow-sm)" : "none",
              }}>
                {t === "preferred" ? `✓ Include (${preferred.length})` : `✗ Exclude (${avoided.length})`}
              </button>
            ))}
          </div>

          {/* Country chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 7, minHeight: 36, marginBottom: 14 }}>
            {activeList.length === 0 ? (
              <span style={{ fontSize: "0.8rem", color: "var(--gray-400)", fontStyle: "italic" }}>
                {tab === "preferred" ? "No countries added yet" : "No countries excluded"}
              </span>
            ) : activeList.map(country => (
              <span key={country} style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "4px 10px 4px 12px",
                borderRadius: 999, fontSize: "0.8rem", fontWeight: 500,
                background: tab === "preferred" ? "var(--blue-bg)" : "var(--red-bg)",
                border: `1px solid ${tab === "preferred" ? "var(--blue-border)" : "var(--red-border)"}`,
                color: tab === "preferred" ? "var(--blue)" : "var(--red)",
              }}>
                {country}
                <button onClick={() => remove(country, tab)} style={{
                  background: "none", border: "none", cursor: "pointer",
                  padding: 0, lineHeight: 1, color: "inherit", opacity: 0.7,
                  display: "flex", alignItems: "center",
                }}>
                  <X style={{ width: 12, height: 12 }} />
                </button>
              </span>
            ))}
          </div>

          {/* Add new country */}
          <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
            <input
              type="text"
              value={newCountry}
              onChange={e => setNew(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add() } }}
              placeholder={`Add country to ${tab} list…`}
              style={{
                flex: 1, padding: "8px 12px", borderRadius: "var(--r-md)",
                border: "1px solid var(--border)", fontSize: "0.85rem",
                outline: "none", background: "var(--white)", color: "var(--navy)",
              }}
            />
            <button onClick={add} className="btn-ghost" style={{ padding: "8px 14px", flexShrink: 0 }}>
              <Plus style={{ width: 14, height: 14 }} />
              Add
            </button>
          </div>

          {/* Save */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button onClick={save} disabled={saving} className="btn-primary" style={{ padding: "8px 18px" }}>
              {saving
                ? <><Loader2 style={{ width: 13, height: 13 }} className="animate-spin" /> Saving…</>
                : <><Save style={{ width: 13, height: 13 }} /> Save Changes</>}
            </button>
            {saved && (
              <span style={{ fontSize: "0.8rem", color: "var(--green)", display: "flex", alignItems: "center", gap: 5 }}>
                <CheckCircle2 style={{ width: 13, height: 13 }} /> Saved
              </span>
            )}
            <span style={{ marginLeft: "auto", fontSize: "0.72rem", color: "var(--gray-400)" }}>
              Changes apply to the next research cycle
            </span>
          </div>
        </>
      )}
    </GlassCard>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────
export default function ResearchPage() {
  const [runs, setRuns]                     = useState<ResearchRun[]>([])
  const [loading, setLoading]               = useState(true)
  const [triggering, setTriggering]         = useState(false)
  const [msg, setMsg]                       = useState<{ text: string; ok: boolean } | null>(null)
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

      {/* Country manager */}
      <CountryManager />

      {/* Schedule */}
      {scheduleStatus && (
        <GlassCard className="fade-up-3" style={{ marginBottom: 18 }}>
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
      <GlassCard className="fade-up-4" noPadding>
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
