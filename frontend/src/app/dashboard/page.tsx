import { api } from "@/lib/api"
import Navbar from "@/components/layout/navbar"
import { timeAgo, scoreColor, formatScore } from "@/lib/utils"
import {
  Activity,
  Database,
  Bot,
  Bell,
  Clock,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
} from "lucide-react"

export const dynamic = "force-dynamic"

export default async function DashboardPage() {
  const [dash, stats] = await Promise.all([
    api.getDashboard().catch(() => null),
    api.getStats().catch(() => null),
  ])

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="mb-8">
          <h1 className="text-white text-3xl font-bold">Dashboard</h1>
          <p className="text-zinc-500 mt-1">
            System status and research overview
            {dash && (
              <span className="ml-2 text-zinc-600 text-sm">
                · updated {timeAgo(dash.generated_at)}
              </span>
            )}
          </p>
        </div>

        {/* Health row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <HealthCard
            icon={<Database className="w-4 h-4" />}
            label="Database"
            ok={dash?.health.database === "connected"}
          />
          <HealthCard
            icon={<Bot className="w-4 h-4" />}
            label="Gemini LLM"
            ok={!!dash?.health.llm_configured}
          />
          <HealthCard
            icon={<Bell className="w-4 h-4" />}
            label="Telegram"
            ok={!!dash?.health.telegram_enabled}
          />
          <HealthCard
            icon={<Activity className="w-4 h-4" />}
            label="Scheduler"
            ok={!!dash?.health.scheduler_running}
          />
        </div>

        {/* Scheduler jobs */}
        {dash?.health.scheduler_jobs && (
          <div className="bg-[#0d1117] border border-white/5 rounded-xl p-5 mb-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" /> Scheduled Jobs
            </h2>
            <div className="grid sm:grid-cols-3 gap-3">
              {dash.health.scheduler_jobs.map((job) => (
                <div key={job.id} className="bg-[#080b12] rounded-lg p-3">
                  <p className="text-zinc-300 text-sm font-medium">{job.name}</p>
                  <p className="text-zinc-600 text-xs mt-1">
                    Next: {job.next_run ? new Date(job.next_run).toLocaleString() : "—"}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Opportunity stats */}
        {dash && (
          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div className="bg-[#0d1117] border border-white/5 rounded-xl p-5">
              <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" /> Opportunities
              </h2>
              <div className="space-y-2">
                {Object.entries(dash.opportunities.by_eligibility).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm">
                    <span className="text-zinc-400 capitalize">{k.replace("_", " ")}</span>
                    <span className="text-white font-medium">{v as number}</span>
                  </div>
                ))}
                <div className="border-t border-white/5 pt-2 flex justify-between text-sm">
                  <span className="text-zinc-400">Free tuition</span>
                  <span className="text-emerald-400 font-medium">
                    {dash.opportunities.free_tuition_count}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Total</span>
                  <span className="text-white font-bold">{dash.opportunities.total}</span>
                </div>
              </div>
            </div>

            <div className="bg-[#0d1117] border border-white/5 rounded-xl p-5">
              <h2 className="text-white font-semibold mb-4">Research Stats</h2>
              <div className="space-y-2">
                <StatRow label="Total found" value={dash.costs.total_opportunities_found} />
                <StatRow label="Pages fetched" value={dash.costs.total_pages_fetched} />
                <StatRow label="Runs completed" value={dash.costs.runs_completed} />
                <StatRow
                  label="Runs with errors"
                  value={dash.costs.runs_with_errors}
                  accent={dash.costs.runs_with_errors > 0 ? "text-orange-400" : "text-white"}
                />
                <StatRow
                  label="LLM cost (total)"
                  value={`$${dash.costs.total_llm_cost_usd.toFixed(4)}`}
                />
              </div>
            </div>
          </div>
        )}

        {/* Recent runs */}
        {dash?.recent_runs && dash.recent_runs.length > 0 && (
          <div className="bg-[#0d1117] border border-white/5 rounded-xl p-5">
            <h2 className="text-white font-semibold mb-4">Recent Research Runs</h2>
            <div className="space-y-3">
              {dash.recent_runs.slice(0, 5).map((run) => (
                <div
                  key={run.id}
                  className="flex items-start justify-between gap-4 py-2 border-b border-white/5 last:border-0"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {run.status === "completed" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : run.status === "partial" ? (
                      <AlertCircle className="w-4 h-4 text-yellow-400 shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="text-zinc-300 text-sm">
                        {new Date(run.started_at).toLocaleString()}
                      </p>
                      <p className="text-zinc-600 text-xs">
                        {run.pages_fetched} pages · {run.opportunities_found} found ·{" "}
                        {run.errors?.length ?? 0} errors
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-xs capitalize shrink-0 ${
                      run.status === "completed"
                        ? "text-emerald-400"
                        : run.status === "partial"
                        ? "text-yellow-400"
                        : "text-red-400"
                    }`}
                  >
                    {run.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </>
  )
}

function HealthCard({
  icon,
  label,
  ok,
}: {
  icon: React.ReactNode
  label: string
  ok: boolean
}) {
  return (
    <div
      className={`bg-[#0d1117] border rounded-xl p-4 flex items-center gap-3 ${
        ok ? "border-white/5" : "border-red-500/20"
      }`}
    >
      <span className={ok ? "text-emerald-400" : "text-red-400"}>{icon}</span>
      <div>
        <p className="text-white text-sm font-medium">{label}</p>
        <p className={`text-xs ${ok ? "text-emerald-400" : "text-red-400"}`}>
          {ok ? "OK" : "Error"}
        </p>
      </div>
    </div>
  )
}

function StatRow({
  label,
  value,
  accent = "text-white",
}: {
  label: string
  value: string | number
  accent?: string
}) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-zinc-400">{label}</span>
      <span className={`font-medium ${accent}`}>{value}</span>
    </div>
  )
}
