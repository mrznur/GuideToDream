"use client"

import { useEffect, useState } from "react"
import PageShell from "@/components/layout/page-shell"
import PageHeader from "@/components/ui/page-header"
import GlassCard from "@/components/ui/glass-card"
import { api, type PipelineSummary } from "@/lib/api"
import { KanbanSquare, ArrowRight } from "lucide-react"
import Link from "next/link"

const STAGES = [
  { key: "discovered",  label: "Discovered",  color: "var(--gray-500)", border: "#c8cfd8", bg: "var(--gray-100)", desc: "Found by research"    },
  { key: "shortlisted", label: "Shortlisted", color: "var(--blue)",      border: "#93c5fd", bg: "var(--blue-bg)",  desc: "Bookmarked"            },
  { key: "preparing",   label: "Preparing",   color: "var(--purple)",    border: "#c4b5fd", bg: "var(--purple-bg)",desc: "Documents in progress" },
  { key: "applied",     label: "Applied",     color: "var(--amber)",     border: "#fcd34d", bg: "var(--amber-bg)", desc: "Submitted"             },
  { key: "interview",   label: "Interview",   color: "#d97706",          border: "#fbbf24", bg: "#fef9c3",         desc: "Invited to interview"  },
  { key: "accepted",    label: "Accepted",    color: "var(--green)",     border: "#a3d9be", bg: "var(--green-bg)", desc: "Offer received 🎉"      },
  { key: "rejected",    label: "Rejected",    color: "var(--red)",       border: "#fca5a5", bg: "var(--red-bg)",   desc: "Not accepted"          },
  { key: "withdrawn",   label: "Withdrawn",   color: "var(--gray-400)",  border: "#c8cfd8", bg: "var(--gray-100)", desc: "Opted out"             },
]
const FLOW = ["discovered", "shortlisted", "preparing", "applied", "accepted"]

function StageCard({ stage, count, opportunityIds }: {
  stage: typeof STAGES[number]; count: number; opportunityIds: string[]
}) {
  const active = count > 0
  return (
    <div style={{
      background: active ? stage.bg : "var(--bg-card)",
      border: `1px solid ${active ? stage.border : "var(--border)"}`,
      borderRadius: "var(--r-lg)",
      borderTop: active ? `3px solid ${stage.color}` : "1px solid var(--border)",
      padding: "16px 18px",
      boxShadow: active ? "var(--shadow-sm)" : "none",
      transition: "all 0.2s",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{
          fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em",
          textTransform: "uppercase", color: active ? stage.color : "var(--gray-400)",
        }}>
          {stage.label}
        </span>
        {active && (
          <span style={{
            width: 8, height: 8, borderRadius: "50%",
            background: stage.color, display: "block",
          }} />
        )}
      </div>

      <div style={{
        fontSize: active ? "2.8rem" : "2.2rem",
        fontWeight: 800, letterSpacing: "-0.05em", lineHeight: 1,
        color: active ? stage.color : "var(--gray-300)",
        marginBottom: 6, transition: "all 0.2s",
      }}>
        {count}
      </div>

      <p style={{ margin: 0, fontSize: "0.72rem", color: active ? "var(--gray-600)" : "var(--gray-400)" }}>
        {active ? `${count} application${count !== 1 ? "s" : ""}` : stage.desc}
      </p>

      {active && opportunityIds.length > 0 && (
        <Link href={`/opportunities/${opportunityIds[0]}`} style={{
          display: "inline-flex", alignItems: "center", gap: 4, marginTop: 10,
          fontSize: "0.72rem", color: stage.color, textDecoration: "none", fontWeight: 600,
        }}>
          Open <ArrowRight style={{ width: 10, height: 10 }} />
        </Link>
      )}
    </div>
  )
}

export default function PipelinePage() {
  const [pipeline, setPipeline] = useState<PipelineSummary | null>(null)
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    api.getPipeline().then(setPipeline).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const active = pipeline?.active ?? 0
  const total  = pipeline?.total  ?? 0

  return (
    <PageShell>
      <PageHeader
        eyebrow="Applications"
        title="Your Pipeline"
        subtitle={pipeline ? `${active} active · ${total} total tracked` : "Track every application from discovery to acceptance"}
      />

      {/* Summary row */}
      {pipeline && (
        <GlassCard className="fade-up-1" style={{ marginBottom: 24, padding: "16px 22px" }}>
          <div style={{ display: "flex", gap: 28, flexWrap: "wrap" }}>
            {[
              { label: "Total",    value: total,  color: "var(--navy)"  },
              { label: "Active",   value: active, color: "var(--blue)"  },
              { label: "Accepted", value: pipeline.pipeline["accepted"]?.count ?? 0, color: "var(--green)" },
              { label: "Applied",  value: pipeline.pipeline["applied"]?.count  ?? 0, color: "var(--amber)" },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div style={{ fontSize: "1.8rem", fontWeight: 800, letterSpacing: "-0.04em", color, lineHeight: 1 }}>
                  {value}
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--gray-400)", marginTop: 3, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  {label}
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Stage grid */}
      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 120 }} />
          ))}
        </div>
      ) : (
        <div className="fade-up-2 stage-grid" style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 12, marginBottom: 28,
        }}>
          {STAGES.map(stage => (
            <StageCard
              key={stage.key}
              stage={stage}
              count={pipeline?.pipeline[stage.key]?.count ?? 0}
              opportunityIds={pipeline?.pipeline[stage.key]?.opportunity_ids ?? []}
            />
          ))}
        </div>
      )}

      {/* Flow diagram */}
      <GlassCard className="fade-up-3">
        <p className="section-label">Standard Flow</p>
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", rowGap: 8, marginBottom: 16 }}>
          {FLOW.map((key, i) => {
            const s     = STAGES.find(st => st.key === key)!
            const count = pipeline?.pipeline[key]?.count ?? 0
            return (
              <div key={key} style={{ display: "flex", alignItems: "center" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: "50%",
                    background: count > 0 ? s.bg : "var(--gray-100)",
                    border: `2px solid ${count > 0 ? s.border : "var(--border)"}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: "0.78rem", fontWeight: 800,
                    color: count > 0 ? s.color : "var(--gray-400)",
                  }}>
                    {count > 0 ? count : i + 1}
                  </div>
                  <span style={{
                    fontSize: "0.6rem", fontWeight: 600, textTransform: "uppercase",
                    letterSpacing: "0.04em",
                    color: count > 0 ? s.color : "var(--gray-400)",
                  }}>
                    {s.label}
                  </span>
                </div>
                {i < FLOW.length - 1 && (
                  <div style={{
                    width: 32, height: 1, margin: "0 4px", marginBottom: 18,
                    background: "var(--border)", flexShrink: 0,
                  }} />
                )}
              </div>
            )
          })}
        </div>
        <p style={{ fontSize: "0.82rem", color: "var(--gray-500)", lineHeight: 1.6, margin: 0 }}>
          Open any opportunity and use the <strong style={{ color: "var(--navy)" }}>Application Tracker</strong> to
          move it through stages. Transitions are enforced — you can&apos;t skip steps.
        </p>
      </GlassCard>
    </PageShell>
  )
}
