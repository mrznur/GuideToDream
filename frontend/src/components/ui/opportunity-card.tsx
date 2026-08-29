import Link from "next/link"
import type { Opportunity } from "@/lib/api"
import {
  cn,
  scoreColor,
  eligibilityColor,
  eligibilityLabel,
  formatTuition,
  formatDeadline,
  formatScore,
} from "@/lib/utils"
import { MapPin, Clock, DollarSign, ExternalLink } from "lucide-react"

interface Props {
  opportunity: Opportunity
  compact?: boolean
}

export default function OpportunityCard({ opportunity: opp, compact }: Props) {
  const prog = opp.programme
  const uni = opp.university
  const score = opp.total_score

  return (
    <Link href={`/opportunities/${opp.id}`} className="block group">
      <div className={cn(
        "bg-[#0d1117] border border-white/5 rounded-xl transition-all duration-200",
        "hover:border-white/10 hover:bg-[#111620]",
        compact ? "p-4" : "p-5"
      )}>
        <div className="flex items-start justify-between gap-3">
          {/* Left content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={cn(
                "text-xs px-2 py-0.5 rounded-full border font-medium",
                eligibilityColor(opp.eligibility_status)
              )}>
                {eligibilityLabel(opp.eligibility_status)}
              </span>
              {opp.is_notable_change && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400">
                  Updated
                </span>
              )}
            </div>

            <h3 className="text-white font-semibold text-sm leading-tight truncate group-hover:text-blue-300 transition-colors">
              {prog?.name ?? "Unknown Programme"}
            </h3>
            <p className="text-zinc-400 text-xs mt-0.5 truncate">
              {uni?.name ?? "Unknown University"}
            </p>

            {!compact && (
              <div className="flex items-center gap-3 mt-2 flex-wrap">
                {uni?.country && (
                  <span className="flex items-center gap-1 text-xs text-zinc-500">
                    <MapPin className="w-3 h-3" />
                    {uni.country}
                  </span>
                )}
                <span className="flex items-center gap-1 text-xs text-zinc-500">
                  <DollarSign className="w-3 h-3" />
                  {formatTuition(prog?.tuition_eur_per_year ?? null, prog?.is_tuition_free ?? false)}
                </span>
                {opp.application_deadline && (
                  <span className={cn(
                    "flex items-center gap-1 text-xs",
                    (opp.days_until_deadline ?? 999) <= 30 ? "text-orange-400" : "text-zinc-500"
                  )}>
                    <Clock className="w-3 h-3" />
                    {formatDeadline(opp.application_deadline, opp.days_until_deadline)}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Score */}
          <div className="flex-shrink-0 text-right">
            <div className={cn(
              "text-2xl font-bold tabular-nums",
              scoreColor(score)
            )}>
              {formatScore(score)}
            </div>
            <div className="text-zinc-600 text-xs">/100</div>
            {opp.application_status && (
              <div className="text-xs mt-1 text-zinc-500 capitalize">
                {opp.application_status}
              </div>
            )}
          </div>
        </div>
      </div>
    </Link>
  )
}
