"use client"

import { useEffect, useState } from "react"
import Navbar from "@/components/layout/navbar"
import OpportunityCard from "@/components/ui/opportunity-card"
import { api, type Opportunity } from "@/lib/api"
import { Filter, SortAsc } from "lucide-react"

const ELIGIBILITY_OPTIONS = [
  { value: "", label: "All" },
  { value: "eligible", label: "Eligible" },
  { value: "probably_eligible", label: "Probably Eligible" },
  { value: "uncertain", label: "Uncertain" },
  { value: "ineligible", label: "Ineligible" },
]

const SORT_OPTIONS = [
  { value: "score", label: "Score" },
  { value: "deadline", label: "Deadline" },
  { value: "discovered", label: "Recently Found" },
]

export default function OpportunitiesPage() {
  const [opps, setOpps] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [eligibility, setEligibility] = useState("")
  const [sortBy, setSortBy] = useState("score")
  const [minScore, setMinScore] = useState(0)

  useEffect(() => {
    setLoading(true)
    api
      .getOpportunities({
        eligibility: eligibility || undefined,
        sort_by: sortBy,
        min_score: minScore > 0 ? minScore : undefined,
      })
      .then((res) => setOpps(res.items))
      .catch(() => setOpps([]))
      .finally(() => setLoading(false))
  }, [eligibility, sortBy, minScore])

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="mb-6">
          <h1 className="text-white text-3xl font-bold">Opportunities</h1>
          <p className="text-zinc-500 mt-1">
            All discovered European Master&apos;s programmes
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <div className="flex items-center gap-2 bg-[#0d1117] border border-white/5 rounded-lg px-3 py-2">
            <Filter className="w-3.5 h-3.5 text-zinc-500" />
            <select
              value={eligibility}
              onChange={(e) => setEligibility(e.target.value)}
              className="bg-transparent text-sm text-zinc-300 outline-none cursor-pointer"
            >
              {ELIGIBILITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value} className="bg-[#0d1117]">
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 bg-[#0d1117] border border-white/5 rounded-lg px-3 py-2">
            <SortAsc className="w-3.5 h-3.5 text-zinc-500" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-transparent text-sm text-zinc-300 outline-none cursor-pointer"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value} className="bg-[#0d1117]">
                  Sort: {o.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 bg-[#0d1117] border border-white/5 rounded-lg px-3 py-2">
            <span className="text-zinc-500 text-xs">Min score:</span>
            <input
              type="number"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="bg-transparent text-sm text-zinc-300 w-12 outline-none"
            />
          </div>
        </div>

        {/* Results */}
        {loading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-[#0d1117] border border-white/5 rounded-xl p-5 animate-pulse h-32" />
            ))}
          </div>
        ) : opps.length === 0 ? (
          <div className="text-center py-20 text-zinc-500">
            No opportunities match your filters
          </div>
        ) : (
          <>
            <p className="text-zinc-600 text-sm mb-4">{opps.length} results</p>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {opps.map((opp) => (
                <OpportunityCard key={opp.id} opportunity={opp} />
              ))}
            </div>
          </>
        )}
      </main>
    </>
  )
}
