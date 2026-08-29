"use client"

import { useState } from "react"
import { api } from "@/lib/api"
import { CheckCircle, Bookmark, FileText, Send, Loader2 } from "lucide-react"

const ACTIONS = [
  { status: "shortlisted", label: "Shortlist", icon: Bookmark, color: "bg-blue-600 hover:bg-blue-500" },
  { status: "preparing", label: "Start Preparing", icon: FileText, color: "bg-purple-600 hover:bg-purple-500" },
  { status: "applied", label: "Mark Applied", icon: Send, color: "bg-yellow-600 hover:bg-yellow-500" },
  { status: "accepted", label: "Accepted!", icon: CheckCircle, color: "bg-emerald-600 hover:bg-emerald-500" },
]

interface Props {
  opportunityId: string
  currentStatus: string | null
}

export default function ApplicationActions({ opportunityId, currentStatus }: Props) {
  const [status, setStatus] = useState(currentStatus)
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState("")

  async function handleAction(newStatus: string) {
    setLoading(newStatus)
    setError("")
    try {
      // Try to create an application first if none exists
      if (!status) {
        try {
          await api.createApplication(opportunityId)
        } catch {
          // Already exists — that's fine
        }
      }
      // Get applications to find the ID
      const apps = await api.getApplications()
      const app = apps.find((a) => a.opportunity_id === opportunityId)
      if (!app) {
        setError("Could not find application record")
        return
      }
      const updated = await api.transitionStatus(app.id, newStatus)
      setStatus(updated.status)
    } catch (e: any) {
      setError(e.message || "Failed to update status")
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="bg-[#0d1117] border border-white/5 rounded-xl p-5">
      <h2 className="text-white font-semibold mb-1">Application Tracker</h2>
      {status && (
        <p className="text-zinc-500 text-sm mb-4">
          Current status:{" "}
          <span className="text-blue-400 font-medium capitalize">{status.replace("_", " ")}</span>
        </p>
      )}
      {!status && (
        <p className="text-zinc-600 text-sm mb-4">Not yet tracked. Add to your pipeline:</p>
      )}

      <div className="flex flex-wrap gap-2">
        {ACTIONS.map(({ status: s, label, icon: Icon, color }) => {
          const isCurrent = status === s
          return (
            <button
              key={s}
              onClick={() => handleAction(s)}
              disabled={!!loading || isCurrent}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                isCurrent ? "bg-white/10 border border-white/20" : color
              }`}
            >
              {loading === s ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Icon className="w-3.5 h-3.5" />
              )}
              {isCurrent ? `✓ ${label}` : label}
            </button>
          )
        })}
      </div>

      {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
    </div>
  )
}
