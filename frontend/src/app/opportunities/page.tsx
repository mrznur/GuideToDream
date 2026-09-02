"use client"

import { useEffect, useState, useCallback } from "react"
import PageShell from "@/components/layout/page-shell"
import PageHeader from "@/components/ui/page-header"
import GlassCard from "@/components/ui/glass-card"
import OpportunityCard from "@/components/ui/opportunity-card"
import { api, type Opportunity } from "@/lib/api"
import { GraduationCap, SlidersHorizontal, X } from "lucide-react"
import Link from "next/link"

type EligFilter = "" | "eligible" | "probably_eligible" | "uncertain" | "ineligible"
type SortOption = "score" | "deadline" | "discovered"

const ELIG_OPTIONS = [
  { value: "" as EligFilter,                  label: "All",      badgeClass: "badge-navy"   },
  { value: "eligible" as EligFilter,          label: "Eligible", badgeClass: "badge-green"  },
  { value: "probably_eligible" as EligFilter, label: "Likely",   badgeClass: "badge-blue"   },
  { value: "uncertain" as EligFilter,         label: "Uncertain",badgeClass: "badge-amber"  },
  { value: "ineligible" as EligFilter,        label: "No Match", badgeClass: "badge-red"    },
]

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "score",      label: "Best Match" },
  { value: "deadline",   label: "Soonest Deadline" },
  { value: "discovered", label: "Newest Found" },
]

function SkeletonGrid() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 160 }} />
      ))}
    </div>
  )
}

export default function OpportunitiesPage() {
  const [opps, setOpps]        = useState<Opportunity[]>([])
  const [total, setTotal]      = useState<number | null>(null)
  const [loading, setLoading]  = useState(true)
  const [error, setError]      = useState<string | null>(null)
  const [elig, setElig]        = useState<EligFilter>("")
  const [sort, setSort]        = useState<SortOption>("score")
  const [minScore, setMinScore]= useState(0)
  const [showFilters, setShow] = useState(false)
  const hasActive = elig !== "" || minScore > 0

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    api.getOpportunities({
      eligibility: elig || undefined,
      sort_by: sort,
      min_score: minScore > 0 ? minScore : undefined,
    })
      .then(res => { setOpps(res.items); setTotal(res.total) })
      .catch(err => {
        setOpps([])
        setTotal(0)
        const msg = err?.name === "AbortError"
          ? "Request timed out. The server may be starting up — try again in a moment."
          : "Couldn't reach the server. Check your connection or try again."
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [elig, sort, minScore])

  useEffect(() => { load() }, [load])
  const reset = () => { setElig(""); setSort("score"); setMinScore(0) }

  return (
    <PageShell>
      <PageHeader
        eyebrow="Programme Discovery"
        title="Opportunities"
        subtitle={total !== null ? `${total} European Master's programmes matched to your profile` : "Matched programmes"}
        action={
          <button onClick={() => setShow(v => !v)} className="btn-ghost" style={{
            borderColor: hasActive ? "var(--navy)" : undefined,
            color: hasActive ? "var(--navy)" : undefined,
            fontWeight: hasActive ? 600 : 400,
          }}>
            <SlidersHorizontal style={{ width: 14, height: 14 }} />
            Filters
            {hasActive && <span style={{
              width: 7, height: 7, borderRadius: "50%",
              background: "var(--gold)", display: "block",
            }} />}
          </button>
        }
      />

      {/* Filter panel */}
      {showFilters && (
        <GlassCard className="fade-up" style={{ marginBottom: 20 }}>
          {/* Eligibility */}
          <div style={{ marginBottom: 18 }}>
            <p className="section-label">Eligibility</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {ELIG_OPTIONS.map(opt => {
                const active = elig === opt.value
                return (
                  <button key={opt.value} onClick={() => setElig(opt.value)} style={{
                    padding: "5px 14px", borderRadius: 999, fontSize: "0.78rem", fontWeight: 600,
                    cursor: "pointer", transition: "all 0.12s",
                    border: active ? "2px solid var(--navy)" : "1px solid var(--border)",
                    background: active ? "var(--navy-faint)" : "var(--white)",
                    color: active ? "var(--navy)" : "var(--gray-600)",
                  }}>
                    {opt.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
            <div>
              <p className="section-label">Sort by</p>
              <div style={{ display: "flex", gap: 6 }}>
                {SORT_OPTIONS.map(opt => {
                  const active = sort === opt.value
                  return (
                    <button key={opt.value} onClick={() => setSort(opt.value)} style={{
                      padding: "5px 12px", borderRadius: "var(--r-md)", fontSize: "0.78rem", fontWeight: 500,
                      cursor: "pointer", whiteSpace: "nowrap", transition: "all 0.12s",
                      border: active ? "2px solid var(--navy)" : "1px solid var(--border)",
                      background: active ? "var(--navy-faint)" : "var(--white)",
                      color: active ? "var(--navy)" : "var(--gray-600)",
                    }}>
                      {opt.label}
                    </button>
                  )
                })}
              </div>
            </div>

            <div style={{ flex: 1, minWidth: 180, maxWidth: 260 }}>
              <p className="section-label">Min Score: {minScore > 0 ? minScore : "Any"}</p>
              <input type="range" min={0} max={100} step={5} value={minScore}
                onChange={e => setMinScore(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--navy)", cursor: "pointer" }} />
            </div>
          </div>

          {hasActive && (
            <div style={{ marginTop: 14, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              <button onClick={reset} style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                fontSize: "0.78rem", color: "var(--gray-500)", background: "none",
                border: "none", cursor: "pointer", padding: 0,
              }}>
                <X style={{ width: 12, height: 12 }} /> Reset all filters
              </button>
            </div>
          )}
        </GlassCard>
      )}

      {/* Active filter chips */}
      {!showFilters && hasActive && (
        <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--gray-400)" }}>Filters:</span>
          {elig && (
            <span className="badge badge-navy" style={{ gap: 6 }}>
              {ELIG_OPTIONS.find(o => o.value === elig)?.label}
              <button onClick={() => setElig("")} style={{ background: "none", border: "none", cursor: "pointer", padding: 0, lineHeight: 1, color: "inherit" }}>
                <X style={{ width: 9, height: 9 }} />
              </button>
            </span>
          )}
          {minScore > 0 && (
            <span className="badge badge-gold" style={{ gap: 6 }}>
              Score ≥ {minScore}
              <button onClick={() => setMinScore(0)} style={{ background: "none", border: "none", cursor: "pointer", padding: 0, lineHeight: 1, color: "inherit" }}>
                <X style={{ width: 9, height: 9 }} />
              </button>
            </span>
          )}
        </div>
      )}

      {/* Count */}
      {!loading && opps.length > 0 && (
        <p style={{ fontSize: "0.8rem", color: "var(--gray-400)", marginBottom: 14 }}>
          {opps.length} result{opps.length !== 1 ? "s" : ""}
          {sort !== "score" && <span> · sorted by <strong>{SORT_OPTIONS.find(s => s.value === sort)?.label}</strong></span>}
        </p>
      )}

      {/* Grid */}
      <div className="fade-up-1">
        {loading ? <SkeletonGrid /> : error ? (
          <GlassCard style={{ padding: "48px 24px", textAlign: "center" }}>
            <div style={{ fontSize: "2rem", marginBottom: 12 }}>⚠️</div>
            <p style={{ margin: "0 0 6px", fontWeight: 700, color: "var(--gray-700)" }}>
              Server unavailable
            </p>
            <p style={{ margin: "0 0 20px", fontSize: "0.85rem", color: "var(--gray-500)" }}>
              {error}
            </p>
            <button onClick={load} className="btn-primary">Try again</button>
          </GlassCard>
        ) : opps.length === 0 ? (
          <GlassCard style={{ padding: "56px 24px", textAlign: "center" }}>
            <GraduationCap style={{ width: 44, height: 44, color: "var(--gray-300)", margin: "0 auto 16px" }} />
            <p style={{ margin: "0 0 6px", fontWeight: 700, fontSize: "1rem", color: "var(--gray-700)" }}>
              {hasActive ? "No results for these filters" : "No opportunities yet"}
            </p>
            <p style={{ margin: "0 0 22px", fontSize: "0.85rem", color: "var(--gray-500)" }}>
              {hasActive ? "Try loosening the filters" : "Run a research cycle to discover programmes"}
            </p>
            {hasActive
              ? <button onClick={reset} className="btn-ghost">Clear filters</button>
              : <Link href="/research" className="btn-primary">Start Research</Link>}
          </GlassCard>
        ) : (
          <div className="grid-cards" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
            {opps.map(opp => <OpportunityCard key={opp.id} opportunity={opp} />)}
          </div>
        )}
      </div>
    </PageShell>
  )
}
