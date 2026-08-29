import ApplicationActions from "@/components/ui/application-actions"
import { api } from "@/lib/api"
import Navbar from "@/components/layout/navbar"
import {
  eligibilityColor,
  eligibilityLabel,
  scoreColor,
  formatScore,
  formatTuition,
  formatDeadline,
} from "@/lib/utils"
import { MapPin, Clock, ExternalLink, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { notFound } from "next/navigation"

export const dynamic = "force-dynamic"

interface Props {
  params: Promise<{ id: string }>
}

export default async function OpportunityDetailPage({ params }: Props) {
  const { id } = await params
  const opp = await api.getOpportunity(id).catch(() => null)
  if (!opp) notFound()

  const prog = opp.programme
  const uni = opp.university
  const score = opp.total_score

  const dimensionLabels: Record<string, string> = {
    academic_fit: "Academic Fit",
    financial_fit: "Financial Fit",
    scholarship_availability: "Scholarship",
    english_feasibility: "English",
    country_preference: "Country",
    portfolio_fit: "Portfolio Fit",
    deadline_urgency: "Deadline Urgency",
    programme_reputation: "Reputation",
  }

  return (
    <>
      <Navbar />
      <main className="pt-14 max-w-4xl mx-auto px-4 sm:px-6 py-10">
        {/* Back */}
        <Link
          href="/opportunities"
          className="flex items-center gap-1.5 text-zinc-500 hover:text-white text-sm mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to opportunities
        </Link>

        {/* Header */}
        <div className="bg-[#0d1117] border border-white/5 rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap gap-2 mb-2">
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${eligibilityColor(opp.eligibility_status)}`}>
                  {eligibilityLabel(opp.eligibility_status)}
                </span>
                {prog?.status === "unverified" && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/30 text-yellow-400">
                    Unverified
                  </span>
                )}
              </div>
              <h1 className="text-white text-2xl font-bold leading-tight">
                {prog?.name ?? "Unknown Programme"}
              </h1>
              <p className="text-zinc-400 mt-1 text-lg">{uni?.name ?? "Unknown University"}</p>
              <div className="flex flex-wrap gap-4 mt-3">
                {uni?.country && (
                  <span className="flex items-center gap-1.5 text-sm text-zinc-500">
                    <MapPin className="w-3.5 h-3.5" /> {uni.country}
                    {uni.city ? `, ${uni.city}` : ""}
                  </span>
                )}
                {opp.application_deadline && (
                  <span className="flex items-center gap-1.5 text-sm text-zinc-500">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDeadline(opp.application_deadline, opp.days_until_deadline)}
                  </span>
                )}
              </div>
            </div>

            {/* Score */}
            <div className="text-center shrink-0">
              <div className={`text-5xl font-bold tabular-nums ${scoreColor(score)}`}>
                {formatScore(score)}
              </div>
              <div className="text-zinc-600 text-sm">/100</div>
              {opp.score_label && (
                <div className="text-zinc-500 text-xs mt-1">{opp.score_label}</div>
              )}
            </div>
          </div>

          {/* Action links */}
          <div className="flex gap-3 mt-5">
            {prog?.official_url && (
              <a href={prog.official_url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors">
                <ExternalLink className="w-3.5 h-3.5" /> Official Page
              </a>
            )}
            {prog?.application_portal_url && (
              <a href={prog.application_portal_url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-4 py-2 bg-white/5 hover:bg-white/10 text-white text-sm rounded-lg border border-white/10 transition-colors">
                <ExternalLink className="w-3.5 h-3.5" /> Apply
              </a>
            )}
          </div>
        </div>

        {/* Score breakdown */}
        {opp.score_breakdown && (
          <div className="bg-[#0d1117] border border-white/5 rounded-xl p-6 mb-6">
            <h2 className="text-white font-semibold mb-4">Score Breakdown</h2>
            <div className="space-y-3">
              {Object.entries(opp.score_breakdown).map(([key, val]) => {
                const pct = Math.round((val as number) * 100)
                return (
                  <div key={key}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-zinc-400">{dimensionLabels[key] ?? key}</span>
                      <span className={scoreColor((val as number) * 100)}>{pct}%</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-blue-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
            {opp.score_explanation && (
              <div className="mt-5 pt-5 border-t border-white/5">
                <h3 className="text-zinc-400 text-xs uppercase tracking-wider mb-2">Explanation</h3>
                <pre className="text-zinc-300 text-sm whitespace-pre-wrap font-sans leading-relaxed">
                  {opp.score_explanation}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Requirements */}
        {prog?.requirements && prog.requirements.length > 0 && (
          <div className="bg-[#0d1117] border border-white/5 rounded-xl p-6 mb-6">
            <h2 className="text-white font-semibold mb-4">Requirements</h2>
            <div className="space-y-3">
              {prog.requirements.map((req, i) => (
                <div key={i} className="bg-[#080b12] rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-zinc-300 capitalize">
                      {req.requirement_type.replace(/_/g, " ")}
                    </span>
                    {req.value && (
                      <span className="text-sm font-bold text-white">{req.value}</span>
                    )}
                    {req.is_strict === true && (
                      <span className="text-xs px-1.5 py-0.5 bg-red-500/10 border border-red-500/30 text-red-400 rounded">Strict</span>
                    )}
                    {req.is_strict === false && (
                      <span className="text-xs px-1.5 py-0.5 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 rounded">Guideline</span>
                    )}
                    {req.is_strict === null && (
                      <span className="text-xs px-1.5 py-0.5 bg-zinc-500/10 border border-zinc-500/30 text-zinc-400 rounded">Unclear</span>
                    )}
                    {req.confidence && (
                      <span className="text-xs text-zinc-600 ml-auto">
                        {Math.round(req.confidence * 100)}% confidence
                      </span>
                    )}
                  </div>
                  {req.raw_text && (
                    <p className="text-zinc-500 text-xs italic">&ldquo;{req.raw_text}&rdquo;</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Application tracker */}
        <ApplicationActions opportunityId={opp.id} currentStatus={opp.application_status} />

        {/* Programme details */}
        <div className="bg-[#0d1117] border border-white/5 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4">Programme Details</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            <Detail label="Degree" value={prog?.degree_type} />
            <Detail label="Field" value={prog?.field} />
            <Detail label="Language" value={prog?.language} />
            <Detail label="Duration" value={prog?.duration_months ? `${prog.duration_months} months` : null} />
            <Detail label="Tuition" value={formatTuition(prog?.tuition_eur_per_year ?? null, prog?.is_tuition_free ?? false)} />
            <Detail label="Intake" value={prog?.intake_months?.join(", ")} />
            {uni?.qs_rank && <Detail label="QS Rank" value={`#${uni.qs_rank}`} />}
          </div>
        </div>
      </main>
    </>
  )
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="flex gap-3">
      <span className="text-zinc-600 text-sm w-24 shrink-0">{label}</span>
      <span className="text-zinc-300 text-sm">{value}</span>
    </div>
  )
}
