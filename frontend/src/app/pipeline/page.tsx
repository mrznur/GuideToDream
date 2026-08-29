"use client"

import { useEffect, useState } from "react"
import Navbar from "@/components/layout/navbar"
import { api, type PipelineSummary } from "@/lib/api"
import { KanbanSquare } from "lucide-react"

const STAGES = [
  { key: "discovered",  label: "Discovered",  color: "#475569", glow: "rgba(71,85,105,0.3)" },
  { key: "shortlisted", label: "Shortlisted", color: "#63b3ed", glow: "rgba(99,179,237,0.3)" },
  { key: "preparing",   label: "Preparing",   color: "#818cf8", glow: "rgba(129,140,248,0.3)" },
  { key: "applied",     label: "Applied",     color: "#fbbf24", glow: "rgba(251,191,36,0.3)" },
  { key: "interview",   label: "Interview",   color: "#f97316", glow: "rgba(249,115,22,0.3)" },
  { key: "accepted",    label: "Accepted",    color: "#34d399", glow: "rgba(52,211,153,0.3)" },
  { key: "rejected",    label: "Rejected",    color: "#f87171", glow: "rgba(248,113,113,0.2)" },
  { key: "withdrawn",   label: "Withdrawn",   color: "#334155", glow: "rgba(51,65,85,0.2)" },
]

export default function PipelinePage() {
  const [pipeline, setPipeline] = useState<PipelineSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getPipeline().then(setPipeline).catch(() => {}).finally(() => setLoading(false))
  }, [])

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-1"
            style={{ background: "linear-gradient(135deg, #f2f4f8, #93c5fd)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Application Pipeline
          </h1>
          <p className="text-slate-500 text-sm">
            {pipeline ? `${pipeline.active} active · ${pipeline.total} total` : "Track your applications through each stage"}
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="rounded-xl h-28 animate-pulse"
                style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(255,255,255,0.04)" }} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {STAGES.map(({ key, label, color, glow }) => {
              const count = pipeline?.pipeline[key]?.count ?? 0
              return (
                <div key={key} className="rounded-xl p-4 transition-all duration-200"
                  style={{
                    background: "rgba(10,14,26,0.8)",
                    border: `1px solid ${count > 0 ? glow : "rgba(255,255,255,0.05)"}`,
                    boxShadow: count > 0 ? `0 0 20px ${glow}` : "none",
                  }}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                      <span className="text-xs font-medium" style={{ color: count > 0 ? color : "#475569" }}>{label}</span>
                    </div>
                    <span className="text-2xl font-bold tabular-nums" style={{ color: count > 0 ? color : "#1e293b" }}>
                      {count}
                    </span>
                  </div>
                  {count === 0
                    ? <p className="text-xs" style={{ color: "#1e293b" }}>Empty</p>
                    : <p className="text-xs" style={{ color: "#475569" }}>
                        {count} application{count > 1 ? "s" : ""}
                      </p>
                  }
                </div>
              )
            })}
          </div>
        )}

        {/* How-to */}
        <div className="mt-8 rounded-xl p-5"
          style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(255,255,255,0.06)" }}>
          <h2 className="text-white font-semibold text-sm mb-3">Moving through the pipeline</h2>
          <p className="text-slate-500 text-sm mb-3">
            Open any opportunity and use the tracker buttons to move it through stages.
            The pipeline enforces valid transitions — you can&apos;t skip steps.
          </p>
          <div className="flex flex-wrap gap-2">
            {["discovered", "→", "shortlisted", "→", "preparing", "→", "applied", "→", "accepted"].map((s, i) => (
              <span key={i} className="text-xs"
                style={{ color: s === "→" ? "#334155" : "#64748b" }}>
                {s}
              </span>
            ))}
          </div>
        </div>
      </main>
    </>
  )
}
