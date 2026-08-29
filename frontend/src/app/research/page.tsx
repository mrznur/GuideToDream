"use client"

import { useState, useEffect } from "react"
import Navbar from "@/components/layout/navbar"
import { api, type ResearchRun } from "@/lib/api"
import { Search, Play, CheckCircle2, AlertCircle, Clock, Loader2 } from "lucide-react"
import { timeAgo } from "@/lib/utils"

export default function ResearchPage() {
  const [runs, setRuns] = useState<ResearchRun[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [msg, setMsg] = useState("")
  const [scheduleStatus, setScheduleStatus] = useState<any>(null)

  useEffect(() => {
    Promise.all([
      api.getRuns(15).then(setRuns).catch(() => {}),
      api.getScheduleStatus().then(setScheduleStatus).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  async function trigger() {
    setTriggering(true)
    setMsg("")
    try {
      await api.triggerResearch()
      setMsg("✅ Research cycle triggered in background. Check back in a few minutes.")
      setTimeout(() => api.getRuns(15).then(setRuns).catch(() => {}), 5000)
    } catch {
      setMsg("❌ Failed to trigger. Check the API is running.")
    } finally {
      setTriggering(false)
    }
  }

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-4xl mx-auto px-4 sm:px-6 py-8">

        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-1"
            style={{ background: "linear-gradient(135deg, #f2f4f8, #34d399)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Research
          </h1>
          <p className="text-slate-500 text-sm">Discover new opportunities from European universities</p>
        </div>

        {/* Trigger card */}
        <div className="rounded-xl p-6 mb-6"
          style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(52,211,153,0.15)" }}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-white font-semibold text-sm mb-1">Run Research Now</h2>
              <p className="text-slate-500 text-xs leading-relaxed max-w-sm">
                Searches for Master&apos;s programmes across Europe, fetches official pages,
                extracts data with AI, and scores against your profile. Runs automatically at 08:00 daily.
              </p>
              {msg && <p className="mt-3 text-xs text-slate-400">{msg}</p>}
            </div>
            <button onClick={trigger} disabled={triggering}
              className="flex-shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-50"
              style={{ background: "linear-gradient(135deg, #059669, #10b981)", boxShadow: triggering ? "none" : "0 0 20px rgba(52,211,153,0.2)" }}>
              {triggering
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Play className="w-4 h-4" />}
              {triggering ? "Running…" : "Run Now"}
            </button>
          </div>
        </div>

        {/* Schedule */}
        {scheduleStatus && (
          <div className="rounded-xl p-5 mb-6"
            style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-white font-semibold text-sm flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-400" />
                Automated Schedule
              </h2>
              <span className="text-xs px-2 py-0.5 rounded-full"
                style={scheduleStatus.running
                  ? { background: "rgba(52,211,153,0.1)", color: "#34d399", border: "1px solid rgba(52,211,153,0.25)" }
                  : { background: "rgba(248,113,113,0.1)", color: "#f87171", border: "1px solid rgba(248,113,113,0.25)" }}>
                {scheduleStatus.running ? "● Active" : "● Stopped"}
              </span>
            </div>
            <div className="space-y-2">
              {(scheduleStatus.jobs ?? []).map((job: any) => (
                <div key={job.id} className="flex justify-between items-center py-1.5 px-3 rounded-lg"
                  style={{ background: "rgba(5,7,13,0.5)" }}>
                  <span className="text-slate-400 text-xs">{job.name}</span>
                  <span className="text-slate-600 text-xs">
                    {job.next_run ? new Date(job.next_run).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Run history */}
        <div className="rounded-xl p-5"
          style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(255,255,255,0.06)" }}>
          <h2 className="text-white font-semibold text-sm mb-4">Run History</h2>
          {loading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-14 rounded-lg animate-pulse"
                  style={{ background: "rgba(255,255,255,0.03)" }} />
              ))}
            </div>
          ) : runs.length === 0 ? (
            <p className="text-slate-600 text-sm">No research runs yet</p>
          ) : (
            <div className="space-y-2">
              {runs.map(run => (
                <div key={run.id} className="flex items-start justify-between gap-4 p-3 rounded-lg"
                  style={{ background: "rgba(5,7,13,0.5)", border: "1px solid rgba(255,255,255,0.03)" }}>
                  <div className="flex items-center gap-2 min-w-0">
                    {run.status === "completed"
                      ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      : run.status === "partial"
                      ? <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                      : run.status === "running"
                      ? <Loader2 className="w-4 h-4 text-blue-400 shrink-0 animate-spin" />
                      : <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />}
                    <div>
                      <p className="text-slate-300 text-xs font-medium">
                        {new Date(run.started_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </p>
                      <div className="flex gap-3 mt-0.5">
                        <span className="text-slate-600 text-xs">{run.queries_generated} queries</span>
                        <span className="text-slate-600 text-xs">{run.pages_fetched} pages</span>
                        <span className="text-emerald-600 text-xs">{run.opportunities_found} found</span>
                        {run.errors?.length > 0 && (
                          <span className="text-amber-600 text-xs">{run.errors.length} errors</span>
                        )}
                        {run.duration_seconds && (
                          <span className="text-slate-700 text-xs">{run.duration_seconds}s</span>
                        )}
                      </div>
                      {run.errors && run.errors.length > 0 && (
                        <p className="text-xs text-red-400/60 mt-1 truncate max-w-xs">
                          [{run.errors[0].stage}] {run.errors[0].error}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className="text-xs shrink-0 capitalize font-medium"
                    style={{ color: run.status === "completed" ? "#34d399" : run.status === "partial" ? "#fbbf24" : run.status === "running" ? "#63b3ed" : "#f87171" }}>
                    {run.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  )
}
