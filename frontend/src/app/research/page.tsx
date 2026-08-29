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
  const [triggerMsg, setTriggerMsg] = useState("")
  const [scheduleStatus, setScheduleStatus] = useState<any>(null)

  useEffect(() => {
    Promise.all([
      api.getRuns(15).then(setRuns).catch(() => {}),
      api.getScheduleStatus().then(setScheduleStatus).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  async function triggerResearch() {
    setTriggering(true)
    setTriggerMsg("")
    try {
      await api.triggerResearch()
      setTriggerMsg("✅ Research cycle triggered! Results will appear in a few minutes.")
      // Refresh runs after 5s
      setTimeout(() => {
        api.getRuns(15).then(setRuns).catch(() => {})
      }, 5000)
    } catch {
      setTriggerMsg("❌ Failed to trigger research. Check the API is running.")
    } finally {
      setTriggering(false)
    }
  }

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <div className="mb-6">
          <h1 className="text-white text-3xl font-bold flex items-center gap-3">
            <Search className="w-7 h-7 text-emerald-400" />
            Research
          </h1>
          <p className="text-zinc-500 mt-1">
            Trigger research cycles and view run history
          </p>
        </div>

        {/* Trigger */}
        <div className="bg-[#0d1117] border border-white/5 rounded-xl p-6 mb-6">
          <h2 className="text-white font-semibold mb-2">Run Research Now</h2>
          <p className="text-zinc-500 text-sm mb-4">
            The automatic cycle runs at 08:00 daily. You can also trigger it manually at any time.
            The cycle searches for European Master&apos;s programmes, fetches real university pages,
            extracts data with AI, and scores opportunities against your profile.
          </p>
          <button
            onClick={triggerResearch}
            disabled={triggering}
            className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {triggering ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {triggering ? "Triggering…" : "Run Research Cycle"}
          </button>
          {triggerMsg && (
            <p className="mt-3 text-sm text-zinc-400">{triggerMsg}</p>
          )}
        </div>

        {/* Schedule */}
        {scheduleStatus && (
          <div className="bg-[#0d1117] border border-white/5 rounded-xl p-5 mb-6">
            <h2 className="text-white font-semibold mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              Automatic Schedule
              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${
                scheduleStatus.running
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                  : "bg-red-500/10 text-red-400 border border-red-500/30"
              }`}>
                {scheduleStatus.running ? "Running" : "Stopped"}
              </span>
            </h2>
            <div className="space-y-2">
              {(scheduleStatus.jobs ?? []).map((job: any) => (
                <div key={job.id} className="flex justify-between text-sm">
                  <span className="text-zinc-400">{job.name}</span>
                  <span className="text-zinc-600">
                    {job.next_run
                      ? new Date(job.next_run).toLocaleString()
                      : "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Run history */}
        <div className="bg-[#0d1117] border border-white/5 rounded-xl p-5">
          <h2 className="text-white font-semibold mb-4">Run History</h2>
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-16 bg-white/5 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : runs.length === 0 ? (
            <p className="text-zinc-600 text-sm">No research runs yet</p>
          ) : (
            <div className="space-y-3">
              {runs.map((run) => (
                <div key={run.id} className="bg-[#080b12] rounded-lg p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-2 min-w-0">
                      {run.status === "completed" ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : run.status === "partial" ? (
                        <AlertCircle className="w-4 h-4 text-yellow-400 shrink-0" />
                      ) : run.status === "running" ? (
                        <Loader2 className="w-4 h-4 text-blue-400 shrink-0 animate-spin" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                      )}
                      <div>
                        <p className="text-zinc-300 text-sm font-medium">
                          {new Date(run.started_at).toLocaleString()}
                        </p>
                        <div className="flex gap-3 mt-0.5 flex-wrap">
                          <span className="text-zinc-600 text-xs">{run.queries_generated} queries</span>
                          <span className="text-zinc-600 text-xs">{run.pages_fetched} pages</span>
                          <span className="text-zinc-600 text-xs">{run.opportunities_found} found</span>
                          {run.errors?.length > 0 && (
                            <span className="text-orange-500 text-xs">{run.errors.length} errors</span>
                          )}
                          {run.duration_seconds && (
                            <span className="text-zinc-700 text-xs">{run.duration_seconds}s</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <span className={`text-xs shrink-0 capitalize ${
                      run.status === "completed" ? "text-emerald-400" :
                      run.status === "partial" ? "text-yellow-400" :
                      run.status === "running" ? "text-blue-400" : "text-red-400"
                    }`}>
                      {run.status}
                    </span>
                  </div>

                  {/* Errors */}
                  {run.errors && run.errors.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-white/5">
                      {run.errors.slice(0, 2).map((err, i) => (
                        <p key={i} className="text-xs text-red-400/70 truncate">
                          [{err.stage}] {err.error}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  )
}
