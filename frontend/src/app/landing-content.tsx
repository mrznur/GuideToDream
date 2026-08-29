"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { api, type QuickStats, type Opportunity } from "@/lib/api"
import OpportunityCard from "@/components/ui/opportunity-card"
import {
  GraduationCap,
  Calendar,
  Activity,
  ArrowRight,
  Search,
  Zap,
  MessageSquare,
} from "lucide-react"

export default function LandingContent() {
  const [stats, setStats] = useState<QuickStats | null>(null)
  const [top, setTop] = useState<Opportunity[]>([])

  useEffect(() => {
    api.getStats().then(setStats).catch(() => {})
    api.getTopOpportunities(3).then(setTop).catch(() => {})
  }, [])

  return (
    <div className="bg-[#05070d]">
      {/* Stats bar */}
      <div className="border-y border-white/5 bg-[#080b12]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6">
          <Stat
            icon={<GraduationCap className="w-4 h-4" />}
            label="Opportunities"
            value={stats?.total_opportunities ?? "—"}
          />
          <Stat
            icon={<Activity className="w-4 h-4" />}
            label="Eligible / Probable"
            value={stats?.eligible_opportunities ?? "—"}
          />
          <Stat
            icon={<Calendar className="w-4 h-4" />}
            label="Deadlines in 30d"
            value={stats?.deadlines_in_30_days ?? "—"}
          />
          <Stat
            icon={<Zap className="w-4 h-4" />}
            label="Scheduler"
            value={stats?.scheduler_running ? "Active" : "Offline"}
            accent={stats?.scheduler_running ? "text-emerald-400" : "text-red-400"}
          />
        </div>
      </div>

      {/* Top opportunities */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-white text-2xl font-bold">Top Matches</h2>
            <p className="text-zinc-500 text-sm mt-1">Highest-scoring opportunities for your profile</p>
          </div>
          <Link
            href="/opportunities"
            className="flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            View all <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {top.length === 0 ? (
          <div className="bg-[#0d1117] border border-white/5 rounded-xl p-10 text-center">
            <GraduationCap className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-400 font-medium">No opportunities yet</p>
            <p className="text-zinc-600 text-sm mt-1">
              Run a research cycle to discover European Master&apos;s programmes
            </p>
            <Link
              href="/research"
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors"
            >
              <Search className="w-4 h-4" /> Start Research
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-3 gap-4">
            {top.map((opp) => (
              <OpportunityCard key={opp.id} opportunity={opp} />
            ))}
          </div>
        )}
      </section>

      {/* Quick actions */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-20">
        <h2 className="text-white text-2xl font-bold mb-6">Quick Actions</h2>
        <div className="grid sm:grid-cols-3 gap-4">
          <ActionCard
            href="/dashboard"
            icon={<Activity className="w-6 h-6 text-blue-400" />}
            title="Dashboard"
            desc="System health, stats, recent runs"
          />
          <ActionCard
            href="/assistant"
            icon={<MessageSquare className="w-6 h-6 text-purple-400" />}
            title="Ask the Assistant"
            desc="Ask anything about your opportunities"
          />
          <ActionCard
            href="/research"
            icon={<Search className="w-6 h-6 text-emerald-400" />}
            title="Run Research"
            desc="Trigger a new discovery cycle"
          />
        </div>
      </section>
    </div>
  )
}

function Stat({
  icon,
  label,
  value,
  accent = "text-white",
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  accent?: string
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 text-zinc-500">{icon}</span>
      <div>
        <div className={`text-2xl font-bold tabular-nums ${accent}`}>{value}</div>
        <div className="text-zinc-500 text-xs mt-0.5">{label}</div>
      </div>
    </div>
  )
}

function ActionCard({
  href,
  icon,
  title,
  desc,
}: {
  href: string
  icon: React.ReactNode
  title: string
  desc: string
}) {
  return (
    <Link href={href} className="group block">
      <div className="bg-[#0d1117] border border-white/5 rounded-xl p-6 hover:border-white/10 hover:bg-[#111620] transition-all">
        <div className="mb-3">{icon}</div>
        <h3 className="text-white font-semibold group-hover:text-blue-300 transition-colors">
          {title}
        </h3>
        <p className="text-zinc-500 text-sm mt-1">{desc}</p>
        <div className="mt-4 flex items-center gap-1 text-xs text-zinc-600 group-hover:text-blue-400 transition-colors">
          Open <ArrowRight className="w-3 h-3" />
        </div>
      </div>
    </Link>
  )
}
