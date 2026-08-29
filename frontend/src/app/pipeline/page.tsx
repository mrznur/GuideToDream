"use client"

import { useEffect, useState } from "react"
import Navbar from "@/components/layout/navbar"
import { api, type PipelineSummary } from "@/lib/api"
import { KanbanSquare } from "lucide-react"

const STAGES = [
  { key: "discovered", label: "Discovered", color: "border-zinc-600" },
  { key: "shortlisted", label: "Shortlisted", color: "border-blue-500/50" },
  { key: "preparing", label: "Preparing", color: "border-purple-500/50" },
  { key: "applied", label: "Applied", color: "border-yellow-500/50" },
  { key: "interview", label: "Interview", color: "border-orange-500/50" },
  { key: "accepted", label: "Accepted", color: "border-emerald-500/50" },
  { key: "rejected", label: "Rejected", color: "border-red-500/50" },
  { key: "withdrawn", label: "Withdrawn", color: "border-zinc-700" },
]

export default function PipelinePage() {
  const [pipeline, setPipeline] = useState<PipelineSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getPipeline()
      .then(setPipeline)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="mb-6">
          <h1 className="text-white text-3xl font-bold flex items-center gap-3">
            <KanbanSquare className="w-7 h-7 text-blue-400" />
            Application Pipeline
          </h1>
          <p className="text-zinc-500 mt-1">
            Track your applications through each stage
            {pipeline && (
              <span className="ml-2 text-zinc-600">
                · {pipeline.active} active, {pipeline.total} total
              </span>
            )}
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-[#0d1117] border border-white/5 rounded-xl p-4 animate-pulse h-32" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {STAGES.map(({ key, label, color }) => {
              const stage = pipeline?.pipeline[key]
              const count = stage?.count ?? 0
              return (
                <div
                  key={key}
                  className={`bg-[#0d1117] border-t-2 ${color} border-x border-b border-white/5 rounded-xl p-4`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-zinc-300 text-sm font-medium">{label}</span>
                    <span className="text-white font-bold text-lg">{count}</span>
                  </div>
                  {count === 0 ? (
                    <p className="text-zinc-700 text-xs">No applications</p>
                  ) : (
                    <div className="space-y-1.5">
                      <p className="text-zinc-500 text-xs">{count} application{count > 1 ? "s" : ""}</p>
                      <a
                        href="/opportunities"
                        className="text-xs text-blue-500 hover:text-blue-400 transition-colors"
                      >
                        View opportunities →
                      </a>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <div className="mt-8 bg-[#0d1117] border border-white/5 rounded-xl p-5">
          <h2 className="text-white font-semibold mb-3">How to update status</h2>
          <p className="text-zinc-500 text-sm">
            Use the API endpoint to transition an application:
          </p>
          <pre className="mt-3 bg-[#080b12] rounded-lg p-4 text-xs text-zinc-400 overflow-x-auto">
{`PATCH /api/v1/applications/{id}/status
{
  "new_status": "shortlisted",
  "notes": "Great programme, worth applying"
}

Valid transitions:
  discovered → shortlisted → preparing → applied → interview → accepted/rejected`}
          </pre>
          <p className="text-zinc-600 text-xs mt-3">
            Full API docs at:{" "}
            <a
              href="https://guidetodream.onrender.com/docs"
              target="_blank"
              className="text-blue-500 hover:text-blue-400"
            >
              guidetodream.onrender.com/docs
            </a>
          </p>
        </div>
      </main>
    </>
  )
}
