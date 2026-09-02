import { api } from "@/lib/api"
import PageShell from "@/components/layout/page-shell"
import PageHeader from "@/components/ui/page-header"
import GlassCard from "@/components/ui/glass-card"
import OpportunityCard from "@/components/ui/opportunity-card"
import { timeAgo } from "@/lib/utils"
import {
  Database, Bot, Bell, Zap, GraduationCap,
  Calendar, CheckCircle2, AlertCircle, ArrowRight,
  Clock, TrendingUp, Activity,
} from "lucide-react"
import Link from "next/link"

export const dynamic = "force-dynamic"

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 6,
      padding: "5px 10px",
      borderRadius: "var(--r-sm)",
      background: ok ? "var(--green-bg)" : "var(--red-bg)",
      border: `1px solid ${ok ? "var(--green-border)" : "var(--red-border)"}`,
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%",
        background: ok ? "var(--green)" : "var(--red)",
        display: "block",
        boxShadow: ok ? "0 0 0 2px rgba(30,122,82,0.2)" : undefined,
      }} />
      <span style={{ fontSize: "0.72rem", fontWeight: 600, color: ok ? "var(--green)" : "var(--red)" }}>
        {label}
      </span>
    </div>
  )
}

function StatCard({ label, value, color, sub, icon: Icon }: {
  label: string; value: string | number; color: string; sub?: string; icon: React.ElementType
}) {
  return (
    <GlassCard style={{ padding: "18px 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div style={{
          width: 36, height: 36, borderRadius: "var(--r-md)",
          background: color + "18",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Icon style={{ width: 17, height: 17, color }} />
        </div>
      </div>
      <div style={{ fontSize: "1.9rem", fontWeight: 800, letterSpacing: "-0.04em", color: "var(--navy)", lineHeight: 1, marginBottom: 4 }}>
        {value}
      </div>
      <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{label}</div>
      {sub && <div style={{ fontSize: "0.68rem", color: "var(--gray-400)", marginTop: 2 }}>{sub}</div>}
    </GlassCard>
  )
}

function PanelHeader({ icon: Icon, title, color = "var(--navy)" }: {
  icon: React.ElementType; title: string; color?: string
}) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "12px 16px",
      borderBottom: "1px solid var(--border)",
      background: "var(--gray-50)",
      borderRadius: "var(--r-lg) var(--r-lg) 0 0",
    }}>
      <Icon style={{ width: 14, height: 14, color }} />
      <span style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "var(--gray-600)" }}>
        {title}
      </span>
    </div>
  )
}

export default async function DashboardPage() {
  const [dash, top, deadlines] = await Promise.all([
    api.getDashboard().catch(() => null),
    api.getTopOpportunities(6).catch(() => []),
    api.getUpcomingDeadlines(30).catch(() => []),
  ])

  const stats  = dash?.opportunities
  const health = dash?.health
  const costs  = dash?.costs

  return (
    <PageShell>
      <PageHeader
        eyebrow="Overview"
        title="Your Path to Europe"
        subtitle={dash
          ? `Updated ${timeAgo(dash.generated_at)} · ${stats?.total ?? 0} opportunities in your database`
          : "European Master's tracking dashboard"}
        action={
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {[
              { label: "Database", ok: health?.database === "connected" },
              { label: "Scheduler", ok: !!health?.scheduler_running },
            ].map(({ label, ok }) => (
              <StatusBadge key={label} label={label} ok={ok} />
            ))}
          </div>
        }
      />

      {/* Stat row */}
      <div className="fade-up-1 stats-grid" style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
        gap: 14,
        marginBottom: 28,
      }}>
        <StatCard icon={GraduationCap} label="Discovered"  value={stats?.total ?? 0}                color="#1d5ca6" sub="total programmes" />
        <StatCard icon={CheckCircle2}  label="Free Tuition" value={stats?.free_tuition_count ?? 0}   color="#1e7a52" sub="no fees" />
        <StatCard icon={Calendar}      label="Deadlines"    value={deadlines.length}                   color="#b45309" sub="in 30 days" />
        <StatCard icon={Activity}      label="LLM Spend"    value={costs ? `$${costs.total_llm_cost_usd.toFixed(3)}` : "—"} color="#5b21b6" sub="total cost" />
      </div>

      {/* Main two-column */}
      <div className="flex-col-mobile" style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20, alignItems: "start" }}>

        {/* Left: top matches */}
        <div className="fade-up-2">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--navy)", margin: 0 }}>Top Matches</h2>
            <Link href="/opportunities" className="link-muted">
              View all <ArrowRight style={{ width: 12, height: 12 }} />
            </Link>
          </div>

          {top.length === 0 ? (
            <GlassCard style={{ padding: "48px 24px", textAlign: "center" }}>
              <GraduationCap style={{ width: 40, height: 40, color: "var(--gray-300)", margin: "0 auto 14px" }} />
              <p style={{ margin: "0 0 6px", fontWeight: 600, color: "var(--gray-700)" }}>No opportunities yet</p>
              <p style={{ margin: "0 0 20px", fontSize: "0.85rem", color: "var(--gray-500)" }}>
                Run a research cycle to start discovering programmes
              </p>
              <Link href="/research" className="btn-primary">Start Research</Link>
            </GlassCard>
          ) : (
            <div className="grid-cards" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
              {top.map(opp => <OpportunityCard key={opp.id} opportunity={opp} />)}
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="fade-up-3" style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Deadlines */}
          {deadlines.length > 0 && (
            <GlassCard noPadding>
              <PanelHeader icon={Calendar} title="Upcoming Deadlines" color="var(--amber)" />
              <div>
                {deadlines.slice(0, 6).map(opp => {
                  const days = opp.days_until_deadline
                  const urgent = (days ?? 99) <= 7
                  return (
                    <Link key={opp.id} href={`/opportunities/${opp.id}`} className="hover-row" style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "9px 16px", textDecoration: "none", borderBottom: "1px solid var(--border)",
                    }}>
                      <div style={{ minWidth: 0 }}>
                        <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--navy)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {opp.programme?.name}
                        </p>
                        <p style={{ margin: 0, fontSize: "0.7rem", color: "var(--gray-500)" }}>
                          {opp.university?.name}
                        </p>
                      </div>
                      <span className={`badge ${urgent ? "badge-red" : "badge-amber"}`} style={{ flexShrink: 0, marginLeft: 8 }}>
                        {days}d
                      </span>
                    </Link>
                  )
                })}
              </div>
            </GlassCard>
          )}

          {/* Scheduler jobs */}
          {health?.scheduler_jobs && health.scheduler_jobs.length > 0 && (
            <GlassCard noPadding>
              <PanelHeader icon={Clock} title="Schedule" color="var(--blue)" />
              {health.scheduler_jobs.map((job: any) => (
                <div key={job.id} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "9px 16px", borderBottom: "1px solid var(--border)", gap: 10,
                }}>
                  <span style={{ fontSize: "0.8rem", color: "var(--gray-700)", fontWeight: 500 }}>{job.name}</span>
                  <span style={{ fontSize: "0.7rem", color: "var(--gray-400)", flexShrink: 0 }}>
                    {job.next_run ? new Date(job.next_run).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "—"}
                  </span>
                </div>
              ))}
            </GlassCard>
          )}

          {/* Recent runs */}
          {dash?.recent_runs && dash.recent_runs.length > 0 && (
            <GlassCard noPadding>
              <PanelHeader icon={TrendingUp} title="Recent Runs" color="var(--green)" />
              {dash.recent_runs.slice(0, 4).map(run => (
                <div key={run.id} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "9px 16px", borderBottom: "1px solid var(--border)", gap: 10,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                    {run.status === "completed"
                      ? <CheckCircle2 style={{ width: 13, height: 13, color: "var(--green)", flexShrink: 0 }} />
                      : <AlertCircle  style={{ width: 13, height: 13, color: "var(--amber)", flexShrink: 0 }} />}
                    <div>
                      <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--gray-700)", fontWeight: 500 }}>
                        {new Date(run.started_at).toLocaleDateString([], { month: "short", day: "numeric" })}
                      </p>
                      <p style={{ margin: 0, fontSize: "0.68rem", color: "var(--gray-400)" }}>
                        {run.pages_fetched}p · {run.opportunities_found} found
                      </p>
                    </div>
                  </div>
                  <span className={`badge ${run.status === "completed" ? "badge-green" : "badge-amber"}`}>
                    {run.status}
                  </span>
                </div>
              ))}
            </GlassCard>
          )}

          {/* Costs */}
          {costs && costs.runs_completed > 0 && (
            <GlassCard>
              <p className="section-label">Usage Summary</p>
              {[
                { label: "Runs completed",  value: costs.runs_completed },
                { label: "Pages fetched",   value: costs.total_pages_fetched.toLocaleString() },
                { label: "Total LLM cost",  value: `$${costs.total_llm_cost_usd.toFixed(4)}` },
                { label: "Avg per run",     value: `$${costs.avg_cost_per_run_usd.toFixed(4)}` },
              ].map(({ label, value }) => (
                <div key={label} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "6px 0", borderBottom: "1px solid var(--border)",
                }}>
                  <span style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{label}</span>
                  <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--navy)" }}>{value}</span>
                </div>
              ))}
            </GlassCard>
          )}
        </div>
      </div>
    </PageShell>
  )
}
