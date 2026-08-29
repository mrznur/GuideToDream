import { api } from "@/lib/api"
import Navbar from "@/components/layout/navbar"
import OpportunityCard from "@/components/ui/opportunity-card"
import { timeAgo } from "@/lib/utils"
import { Activity, Database, Bot, Bell, Clock, GraduationCap, Calendar, CheckCircle2, AlertCircle, Zap, ArrowRight } from "lucide-react"
import Link from "next/link"

export const dynamic = "force-dynamic"

export default async function DashboardPage() {
  const [dash, top, deadlines] = await Promise.all([
    api.getDashboard().catch(() => null),
    api.getTopOpportunities(6).catch(() => []),
    api.getUpcomingDeadlines(30).catch(() => []),
  ])

  const stats = dash?.opportunities
  const health = dash?.health

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-7xl mx-auto px-4 sm:px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-1"
            style={{ background: "linear-gradient(135deg, #f2f4f8, #93c5fd)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Dashboard
          </h1>
          <p className="text-slate-500 text-sm">
            {dash ? `Updated ${timeAgo(dash.generated_at)}` : "Your European Masters Intelligence Agent"}
          </p>
        </div>

        {/* Status row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            { icon: Database, label: "Database", ok: health?.database === "connected" },
            { icon: Bot, label: "AI Model", ok: !!health?.llm_configured },
            { icon: Bell, label: "Telegram", ok: !!health?.telegram_enabled },
            { icon: Zap, label: "Scheduler", ok: !!health?.scheduler_running },
          ].map(({ icon: Icon, label, ok }) => (
            <div key={label} className="rounded-xl p-3 flex items-center gap-3 transition-all duration-200"
              style={{ background: "rgba(10,14,26,0.8)", border: `1px solid ${ok ? "rgba(52,211,153,0.2)" : "rgba(248,113,113,0.2)"}` }}>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{ background: ok ? "rgba(52,211,153,0.1)" : "rgba(248,113,113,0.1)" }}>
                <Icon className="w-3.5 h-3.5" style={{ color: ok ? "#34d399" : "#f87171" }} />
              </div>
              <div>
                <p className="text-white text-xs font-medium">{label}</p>
                <p className="text-xs" style={{ color: ok ? "#34d399" : "#f87171" }}>{ok ? "Online" : "Offline"}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {[
            { label: "Total Discovered", value: stats?.total ?? 0, color: "#63b3ed" },
            { label: "Free Tuition", value: stats?.free_tuition_count ?? 0, color: "#34d399" },
            { label: "Deadlines Soon", value: deadlines.length, color: "#fbbf24" },
            { label: "Scheduler Jobs", value: health?.scheduler_jobs?.length ?? 0, color: "#818cf8" },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-xl p-4 transition-all duration-200"
              style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(255,255,255,0.06)" }}>
              <p className="text-3xl font-bold tabular-nums mb-1" style={{ color }}>{value}</p>
              <p className="text-slate-500 text-xs">{label}</p>
            </div>
          ))}
        </div>

        {/* Scheduler */}
        {health?.scheduler_jobs && health.scheduler_jobs.length > 0 && (
          <div className="rounded-xl p-5 mb-6"
            style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <h2 className="text-white font-semibold text-sm mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              Automated Schedule
            </h2>
            <div className="grid sm:grid-cols-3 gap-3">
              {health.scheduler_jobs.map((job) => (
                <div key={job.id} className="rounded-lg p-3"
                  style={{ background: "rgba(5,7,13,0.6)", border: "1px solid rgba(255,255,255,0.04)" }}>
                  <p className="text-slate-300 text-xs font-medium mb-1">{job.name}</p>
                  <p className="text-slate-600 text-xs">
                    {job.next_run ? new Date(job.next_run).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top opportunities */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-semibold text-sm flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-blue-400" />
              Top Opportunities
            </h2>
            <Link href="/opportunities"
              className="text-xs text-slate-500 hover:text-blue-400 flex items-center gap-1 transition-colors">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {top.length === 0 ? (
            <div className="rounded-xl p-10 text-center"
              style={{ background: "rgba(10,14,26,0.8)", border: "1px dashed rgba(255,255,255,0.08)" }}>
              <GraduationCap className="w-8 h-8 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500 text-sm font-medium">No opportunities yet</p>
              <p className="text-slate-700 text-xs mt-1">Go to Research and trigger a cycle</p>
              <Link href="/research"
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors"
                style={{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}>
                Start Research
              </Link>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {top.map(opp => <OpportunityCard key={opp.id} opportunity={opp} />)}
            </div>
          )}
        </div>

        {/* Upcoming deadlines */}
        {deadlines.length > 0 && (
          <div className="rounded-xl p-5"
            style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(251,191,36,0.15)" }}>
            <h2 className="font-semibold text-sm mb-4 flex items-center gap-2"
              style={{ color: "#fbbf24" }}>
              <Calendar className="w-4 h-4" />
              Deadlines in next 30 days
            </h2>
            <div className="space-y-2">
              {deadlines.map(opp => {
                const days = opp.days_until_deadline
                const urgent = (days ?? 99) <= 7
                return (
                  <Link href={`/opportunities/${opp.id}`} key={opp.id}
                    className="flex items-center justify-between py-2 px-3 rounded-lg transition-colors hover:bg-white/3">
                    <div className="min-w-0">
                      <p className="text-white text-sm truncate">{opp.programme?.name}</p>
                      <p className="text-slate-500 text-xs">{opp.university?.name}</p>
                    </div>
                    <span className="text-xs font-medium ml-4 shrink-0"
                      style={{ color: urgent ? "#f87171" : "#fbbf24" }}>
                      {days}d left
                    </span>
                  </Link>
                )
              })}
            </div>
          </div>
        )}

        {/* Recent runs */}
        {dash?.recent_runs && dash.recent_runs.length > 0 && (
          <div className="rounded-xl p-5 mt-6"
            style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <h2 className="text-white font-semibold text-sm mb-4">Recent Research Runs</h2>
            <div className="space-y-2">
              {dash.recent_runs.slice(0, 4).map(run => (
                <div key={run.id} className="flex items-center justify-between py-2 px-3 rounded-lg"
                  style={{ background: "rgba(5,7,13,0.5)" }}>
                  <div className="flex items-center gap-2 min-w-0">
                    {run.status === "completed"
                      ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      : <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />}
                    <span className="text-slate-400 text-xs truncate">
                      {new Date(run.started_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0 ml-3">
                    <span className="text-slate-600 text-xs">{run.pages_fetched}p</span>
                    <span className="text-slate-600 text-xs">{run.opportunities_found} found</span>
                    <span className="text-xs capitalize" style={{ color: run.status === "completed" ? "#34d399" : "#fbbf24" }}>
                      {run.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </>
  )
}
