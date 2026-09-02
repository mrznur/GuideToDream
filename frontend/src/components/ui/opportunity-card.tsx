"use client"

import Link from "next/link"
import type { Opportunity } from "@/lib/api"
import { formatTuition, formatDeadline } from "@/lib/utils"
import { MapPin, Clock, ChevronRight } from "lucide-react"

const FLAGS: Record<string, string> = {
  Germany: "🇩🇪", Netherlands: "🇳🇱", "Czech Republic": "🇨🇿",
  Poland: "🇵🇱", Hungary: "🇭🇺", Finland: "🇫🇮", Austria: "🇦🇹",
  Norway: "🇳🇴", Sweden: "🇸🇪", Denmark: "🇩🇰", France: "🇫🇷",
  Belgium: "🇧🇪", Switzerland: "🇨🇭", Italy: "🇮🇹", Spain: "🇪🇸",
  Portugal: "🇵🇹", Ireland: "🇮🇪", Estonia: "🇪🇪",
}

const ELIG = {
  eligible:          { label: "Eligible",    badgeClass: "badge-green",  dot: "var(--green)"  },
  probably_eligible: { label: "Likely",      badgeClass: "badge-blue",   dot: "var(--blue)"   },
  uncertain:         { label: "Uncertain",   badgeClass: "badge-amber",  dot: "var(--amber)"  },
  ineligible:        { label: "No Match",    badgeClass: "badge-red",    dot: "var(--red)"    },
} as const

function ScoreCircle({ score }: { score: number | null }) {
  const s = score ?? 0
  const size = 54
  const r = 20
  const circ = 2 * Math.PI * r
  const fill = (s / 100) * circ
  const color = s >= 75 ? "var(--green)" : s >= 60 ? "var(--blue)" : s >= 45 ? "var(--amber)" : "var(--gray-400)"
  const stroke = s >= 75 ? "#1e7a52" : s >= 60 ? "#1d5ca6" : s >= 45 ? "#b45309" : "#96a3b3"

  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)", display: "block" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--gray-200)" strokeWidth="3.5" />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={stroke} strokeWidth="3.5"
          strokeDasharray={`${fill} ${circ}`} strokeLinecap="round" />
      </svg>
      <div style={{
        position: "absolute", inset: 0,
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        gap: 0,
      }}>
        <span style={{ fontSize: "0.78rem", fontWeight: 800, color, lineHeight: 1 }}>
          {score !== null ? Math.round(score) : "—"}
        </span>
        {score !== null && (
          <span style={{ fontSize: "0.45rem", color: "var(--gray-400)", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
            score
          </span>
        )}
      </div>
    </div>
  )
}

export default function OpportunityCard({ opportunity: opp }: { opportunity: Opportunity }) {
  const prog = opp.programme
  const uni  = opp.university
  const elig = ELIG[opp.eligibility_status as keyof typeof ELIG] ?? ELIG.uncertain
  const flag = uni?.country ? FLAGS[uni.country] : null
  const urgent = (opp.days_until_deadline ?? 999) <= 14

  return (
    <Link href={`/opportunities/${opp.id}`} style={{ textDecoration: "none", display: "block" }}>
      <div style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        padding: "16px 18px",
        transition: "box-shadow 0.18s, border-color 0.18s, transform 0.15s",
        cursor: "pointer",
        position: "relative",
      }}
        onMouseEnter={e => {
          const el = e.currentTarget
          el.style.boxShadow = "var(--shadow-md)"
          el.style.borderColor = "var(--gray-300)"
          el.style.transform = "translateY(-2px)"
        }}
        onMouseLeave={e => {
          const el = e.currentTarget
          el.style.boxShadow = "var(--shadow-sm)"
          el.style.borderColor = "var(--border)"
          el.style.transform = "translateY(0)"
        }}
      >
        {/* Notable change badge */}
        {opp.is_notable_change && (
          <span className="badge badge-gold" style={{
            position: "absolute", top: 12, right: 12,
            fontSize: "0.6rem",
          }}>
            Updated
          </span>
        )}

        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          {/* Left */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Eligibility */}
            <span className={`badge ${elig.badgeClass}`} style={{ marginBottom: 8, display: "inline-flex" }}>
              <span style={{
                width: 5, height: 5, borderRadius: "50%",
                background: elig.dot, display: "block", flexShrink: 0,
              }} />
              {elig.label}
            </span>

            {/* Programme name */}
            <h3 style={{
              margin: "0 0 3px",
              fontSize: "0.9rem",
              fontWeight: 700,
              color: "var(--navy)",
              lineHeight: 1.3,
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
            }}>
              {prog?.name ?? "Unknown Programme"}
            </h3>

            {/* University */}
            <p style={{
              margin: "0 0 10px",
              fontSize: "0.8rem",
              color: "var(--gray-600)",
              fontWeight: 500,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {flag && <span style={{ marginRight: 4 }}>{flag}</span>}
              {uni?.name ?? "Unknown University"}
            </p>

            {/* Meta chips */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
              {/* Tuition */}
              <span style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 3,
                fontSize: "0.7rem",
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: 999,
                background: (prog?.is_tuition_free || prog?.tuition_eur_per_year === 0)
                  ? "var(--green-bg)" : "var(--gray-100)",
                color: (prog?.is_tuition_free || prog?.tuition_eur_per_year === 0)
                  ? "var(--green)" : "var(--gray-600)",
                border: `1px solid ${(prog?.is_tuition_free || prog?.tuition_eur_per_year === 0)
                  ? "var(--green-border)" : "var(--border)"}`,
              }}>
                {formatTuition(prog?.tuition_eur_per_year ?? null, prog?.is_tuition_free ?? false)}
              </span>

              {/* Deadline */}
              {opp.application_deadline && (
                <span style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 3,
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: 999,
                  background: urgent ? "var(--red-bg)" : "var(--amber-bg)",
                  color: urgent ? "var(--red)" : "var(--amber)",
                  border: `1px solid ${urgent ? "var(--red-border)" : "var(--amber-border)"}`,
                }}>
                  <Clock style={{ width: 9, height: 9 }} />
                  {opp.days_until_deadline !== null ? `${opp.days_until_deadline}d` : "deadline"}
                </span>
              )}

              {/* Country */}
              {uni?.country && (
                <span style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 3,
                  fontSize: "0.7rem",
                  fontWeight: 500,
                  padding: "2px 8px",
                  borderRadius: 999,
                  background: "var(--gray-100)",
                  color: "var(--gray-500)",
                  border: "1px solid var(--border)",
                }}>
                  <MapPin style={{ width: 9, height: 9 }} />
                  {uni.country}
                </span>
              )}
            </div>
          </div>

          {/* Right: score + arrow */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
            <ScoreCircle score={opp.total_score} />
            <ChevronRight style={{ width: 14, height: 14, color: "var(--gray-300)" }} />
          </div>
        </div>

        {/* Application status */}
        {opp.application_status && opp.application_status !== "discovered" && (
          <div style={{
            marginTop: 12,
            paddingTop: 10,
            borderTop: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: "50%",
              background: "var(--blue)", display: "block",
            }} />
            <span style={{
              fontSize: "0.72rem",
              color: "var(--blue)",
              fontWeight: 600,
              textTransform: "capitalize",
            }}>
              {opp.application_status.replace(/_/g, " ")}
            </span>
          </div>
        )}
      </div>
    </Link>
  )
}
