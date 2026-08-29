import Link from "next/link"
import type { Opportunity } from "@/lib/api"
import { cn, formatTuition, formatDeadline } from "@/lib/utils"
import { MapPin, Clock, Layers } from "lucide-react"

const COUNTRY_FLAGS: Record<string, string> = {
  Germany: "🇩🇪", Netherlands: "🇳🇱", "Czech Republic": "🇨🇿",
  Poland: "🇵🇱", Hungary: "🇭🇺", Finland: "🇫🇮", Austria: "🇦🇹",
  Norway: "🇳🇴", Sweden: "🇸🇪", Denmark: "🇩🇰", France: "🇫🇷",
  Belgium: "🇧🇪", Switzerland: "🇨🇭", Italy: "🇮🇹", Spain: "🇪🇸",
}

const ELIGIBILITY_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  eligible:          { label: "Eligible",          color: "text-emerald-400", dot: "bg-emerald-400" },
  probably_eligible: { label: "Probably Eligible", color: "text-blue-400",    dot: "bg-blue-400" },
  uncertain:         { label: "Uncertain",          color: "text-amber-400",   dot: "bg-amber-400" },
  ineligible:        { label: "Ineligible",         color: "text-red-400",     dot: "bg-red-400" },
}

function ScoreRing({ score }: { score: number | null }) {
  const s = score ?? 0
  const color = s >= 75 ? "#34d399" : s >= 60 ? "#63b3ed" : s >= 45 ? "#fbbf24" : "#f87171"
  const size = 52
  const r = 20
  const circ = 2 * Math.PI * r
  const dash = (s / 100) * circ

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none"
          stroke="rgba(255,255,255,0.05)" strokeWidth="3" />
        <circle cx={size/2} cy={size/2} r={r} fill="none"
          stroke={color} strokeWidth="3"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 0.5s ease", filter: `drop-shadow(0 0 4px ${color}66)` }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-bold" style={{ color }}>{score ? Math.round(score) : "—"}</span>
      </div>
    </div>
  )
}

interface Props { opportunity: Opportunity; compact?: boolean }

export default function OpportunityCard({ opportunity: opp, compact }: Props) {
  const prog = opp.programme
  const uni = opp.university
  const elig = ELIGIBILITY_CONFIG[opp.eligibility_status] ?? ELIGIBILITY_CONFIG.uncertain
  const country = uni?.country
  const flag = country ? COUNTRY_FLAGS[country] : null

  return (
    <Link href={`/opportunities/${opp.id}`} className="block group">
      <div
        className="relative rounded-xl p-4 transition-all duration-300 overflow-hidden"
        style={{
          background: "rgba(10,14,26,0.8)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLElement).style.border = "1px solid rgba(99,179,237,0.25)"
          ;(e.currentTarget as HTMLElement).style.background = "rgba(15,21,37,0.9)"
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLElement).style.border = "1px solid rgba(255,255,255,0.06)"
          ;(e.currentTarget as HTMLElement).style.background = "rgba(10,14,26,0.8)"
        }}
      >
        {/* Subtle top gradient accent */}
        <div className="absolute top-0 left-0 right-0 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{ background: "linear-gradient(90deg, transparent, rgba(99,179,237,0.4), transparent)" }} />

        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            {/* Eligibility badge */}
            <div className="flex items-center gap-1.5 mb-2">
              <span className={cn("w-1.5 h-1.5 rounded-full", elig.dot)}
                style={{ animation: opp.eligibility_status === "eligible" ? "pulse-dot 2s infinite" : undefined }} />
              <span className={cn("text-xs font-medium", elig.color)}>{elig.label}</span>
              {opp.is_notable_change && (
                <span className="ml-1 text-xs px-1.5 py-0.5 rounded-full text-purple-300"
                  style={{ background: "rgba(168,85,247,0.15)", border: "1px solid rgba(168,85,247,0.3)" }}>
                  Updated
                </span>
              )}
            </div>

            {/* Programme name */}
            <h3 className="text-white font-semibold text-sm leading-tight mb-0.5 truncate group-hover:text-blue-200 transition-colors">
              {prog?.name ?? "Unknown Programme"}
            </h3>

            {/* University */}
            <p className="text-slate-500 text-xs truncate mb-2">
              {flag && <span className="mr-1">{flag}</span>}
              {uni?.name ?? "Unknown University"}
            </p>

            {/* Meta row */}
            {!compact && (
              <div className="flex items-center gap-3 flex-wrap">
                {country && (
                  <span className="flex items-center gap-1 text-xs text-slate-600">
                    <MapPin className="w-3 h-3" />{country}
                  </span>
                )}
                <span className="flex items-center gap-1 text-xs"
                  style={{ color: prog?.is_tuition_free || prog?.tuition_eur_per_year === 0 ? "#34d399" : "#64748b" }}>
                  {formatTuition(prog?.tuition_eur_per_year ?? null, prog?.is_tuition_free ?? false)}
                </span>
                {opp.application_deadline && (
                  <span className={cn(
                    "flex items-center gap-1 text-xs",
                    (opp.days_until_deadline ?? 999) <= 30 ? "text-amber-400" : "text-slate-600"
                  )}>
                    <Clock className="w-3 h-3" />
                    {formatDeadline(opp.application_deadline, opp.days_until_deadline)}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Score ring */}
          <ScoreRing score={opp.total_score} />
        </div>

        {/* Application status pill */}
        {opp.application_status && opp.application_status !== "discovered" && (
          <div className="mt-3 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            <span className="text-xs text-slate-500 capitalize">
              <Layers className="w-3 h-3 inline mr-1 text-blue-400" />
              {opp.application_status.replace("_", " ")}
            </span>
          </div>
        )}
      </div>
    </Link>
  )
}
