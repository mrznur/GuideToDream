"use client"

import { useEffect, useState } from "react"
import Navbar from "@/components/layout/navbar"
import OpportunityCard from "@/components/ui/opportunity-card"
import { api, type Opportunity } from "@/lib/api"
import { Filter, SortAsc, GraduationCap, Search } from "lucide-react"

const ELIGIBILITY_OPTIONS = [
  { value: "", label: "All Eligibility" },
  { value: "eligible", label: "✅ Eligible" },
  { value: "probably_eligible", label: "🔵 Probably Eligible" },
  { value: "uncertain", label: "🟡 Uncertain" },
  { value: "ineligible", label: "🔴 Ineligible" },
]

const SORT_OPTIONS = [
  { value: "score", label: "Highest Score" },
  { value: "deadline", label: "Soonest Deadline" },
  { value: "discovered", label: "Recently Found" },
]

function SelectFilter({ value, onChange, options }: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      className="rounded-lg px-3 py-2 text-xs text-slate-300 outline-none cursor-pointer transition-colors"
      style={{ background: "rgba(10,14,26,0.9)", border: "1px solid rgba(255,255,255,0.08)" }}>
      {options.map(o => (
        <option key={o.value} value={o.value} style={{ background: "#0a0e1a" }}>{o.label}</option>
      ))}
    </select>
  )
}

export default function OpportunitiesPage() {
  const [opps, setOpps] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [eligibility, setEligibility] = useState("")
  const [sortBy, setSortBy] = useState("score")
  const [minScore, setMinScore] = useState(0)

  useEffect(() => {
    setLoading(true)
    api.getOpportunities({
      eligibility: eligibility || undefined,
      sort_by: sortBy,
      min_score: minScore > 0 ? minScore : undefined,
    })
      .then(res => setOpps(res.items))
      .catch(() => setOpps([]))
      .finally(() => setLoading(false))
  }, [eligibility, sortBy, minScore])

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-7xl mx-auto px-4 sm:px-6 py-8">

        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-1"
            style={{ background: "linear-gradient(135deg, #f2f4f8, #93c5fd)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Opportunities
          </h1>
          <p className="text-slate-500 text-sm">European Master's programmes matched to your profile</p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-6">
          <SelectFilter value={eligibility} onChange={setEligibility} options={ELIGIBILITY_OPTIONS} />
          <SelectFilter value={sortBy} onChange={setSortBy} options={SORT_OPTIONS} />
          <div className="flex items-center gap-2 rounded-lg px-3 py-2"
            style={{ background: "rgba(10,14,26,0.9)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <span className="text-slate-500 text-xs">Min score</span>
            <input type="number" min={0} max={100} value={minScore}
              onChange={e => setMinScore(Number(e.target.value))}
              className="bg-transparent text-xs text-slate-300 w-10 outline-none" />
          </div>
        </div>

        {loading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="rounded-xl h-28 animate-pulse"
                style={{ background: "rgba(10,14,26,0.8)", border: "1px solid rgba(255,255,255,0.04)" }} />
            ))}
          </div>
        ) : opps.length === 0 ? (
          <div className="text-center py-20">
            <GraduationCap className="w-10 h-10 text-slate-700 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No opportunities match your filters</p>
          </div>
        ) : (
          <>
            <p className="text-slate-600 text-xs mb-4">{opps.length} results</p>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {opps.map(opp => <OpportunityCard key={opp.id} opportunity={opp} />)}
            </div>
          </>
        )}
      </main>
    </>
  )
}
