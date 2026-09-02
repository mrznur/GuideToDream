import ApplicationActions from "@/components/ui/application-actions"
import GlassCard from "@/components/ui/glass-card"
import PageShell from "@/components/layout/page-shell"
import { api } from "@/lib/api"
import { formatTuition, formatDeadline } from "@/lib/utils"
import { MapPin, Clock, ExternalLink, ArrowLeft, Star } from "lucide-react"
import Link from "next/link"
import { notFound } from "next/navigation"

export const dynamic = "force-dynamic"

interface Props {
  params: Promise<{ id: string }>
}

const DIMENSION_LABELS: Record<string, string> = {
  academic_fit:             "Academic Fit",
  financial_fit:            "Financial Fit",
  scholarship_availability: "Scholarship",
  english_feasibility:      "English",
  country_preference:       "Country Pref",
  portfolio_fit:            "Portfolio",
  deadline_urgency:         "Deadline",
  programme_reputation:     "Reputation",
}

const ELIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  eligible:          { label: "Eligible",        color: "var(--sage)",   bg: "rgba(95,196,168,0.10)",  border: "rgba(95,196,168,0.30)"  },
  probably_eligible: { label: "Likely Eligible", color: "var(--sky)",    bg: "rgba(126,206,232,0.10)", border: "rgba(126,206,232,0.30)" },
  uncertain:         { label: "Uncertain",        color: "var(--amber)",  bg: "rgba(212,146,74,0.10)", border: "rgba(212,146,74,0.30)"  },
  ineligible:        { label: "Ineligible",       color: "var(--rose)",   bg: "rgba(212,96,112,0.08)", border: "rgba(212,96,112,0.25)"  },
}

function scoreColor(s: number | null) {
  if (!s) return "var(--chalk-500)"
  return s >= 80 ? "var(--sage)" : s >= 65 ? "var(--sky)" : s >= 50 ? "var(--amber)" : "var(--rose)"
}

function scorePx(s: number | null) {
  // Same logic but returns a hex/rgba for drop-shadows (can't shadow CSS vars directly)
  if (!s) return "#52596a"
  return s >= 80 ? "#5fc4a8" : s >= 65 ? "#7ecee8" : s >= 50 ? "#d4924a" : "#d46070"
}

function Detail({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div style={{
      display: "flex", gap: 12, padding: "8px 0",
      borderBottom: "1px solid rgba(126,206,232,0.07)",
    }}>
      <span style={{ fontSize: "0.73rem", color: "var(--chalk-500)", width: 110, flexShrink: 0, fontWeight: 500 }}>
        {label}
      </span>
      <span style={{ fontSize: "0.82rem", color: "var(--text-primary)", fontWeight: 500 }}>{value}</span>
    </div>
  )
}

// ─── Section label ────────────────────────────────────────────────────────
function SLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.1em",
      textTransform: "uppercase", color: "var(--chalk-400)", marginBottom: 14,
    }}>
      {children}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────
export default async function OpportunityDetailPage({ params }: Props) {
  const { id } = await params
  const opp = await api.getOpportunity(id).catch(() => null)
  if (!opp) notFound()

  const prog  = opp.programme
  const uni   = opp.university
  const score = opp.total_score
  const elig  = ELIG[opp.eligibility_status] ?? ELIG.uncertain
  const col   = scoreColor(score)
  const colPx = scorePx(score)

  return (
    <PageShell maxWidth={860}>

      {/* Back link */}
      <Link href="/opportunities" style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        fontSize: "0.78rem", color: "var(--chalk-400)", textDecoration: "none",
        marginBottom: 22, fontWeight: 500, transition: "color 0.15s",
      }}>
        <ArrowLeft style={{ width: 12, height: 12 }} />
        Back to Opportunities
      </Link>

      {/* ── Header ──────────────────────────────────────────────────── */}
      <GlassCard accent={colPx} style={{ marginBottom: 14 }}>
        {/* Score glow (decorative) */}
        <div style={{
          position: "absolute", top: -30, right: -30,
          width: 180, height: 180, borderRadius: "50%",
          background: colPx, opacity: 0.06,
          filter: "blur(50px)", pointerEvents: "none",
        }} />

        <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
          {/* Left: info */}
          <div style={{ flex: 1, minWidth: 260 }}>
            {/* Eligibility + unverified badges */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
              <span style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                padding: "4px 12px", borderRadius: 999,
                fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.07em",
                textTransform: "uppercase", color: elig.color,
                background: elig.bg, border: `1px solid ${elig.border}`,
              }}>
                <span style={{
                  width: 5, height: 5, borderRadius: "50%",
                  background: elig.color, display: "block",
                  boxShadow: `0 0 6px ${elig.color}`,
                }} />
                {elig.label}
              </span>
              {prog?.status === "unverified" && (
                <span style={{
                  padding: "4px 10px", borderRadius: 999,
                  fontSize: "0.68rem", fontWeight: 600,
                  color: "var(--amber)",
                  background: "rgba(212,146,74,0.10)",
                  border: "1px solid rgba(212,146,74,0.25)",
                }}>
                  Unverified data
                </span>
              )}
            </div>

            <h1 style={{
              margin: "0 0 8px",
              fontSize: "clamp(1.25rem, 2.5vw, 1.75rem)",
              fontWeight: 800, letterSpacing: "-0.025em",
              lineHeight: 1.15, color: "var(--text-primary)",
            }}>
              {prog?.name ?? "Unknown Programme"}
            </h1>
            <p style={{ margin: "0 0 14px", fontSize: "0.95rem", color: "var(--chalk-300)", fontWeight: 500 }}>
              {uni?.name ?? "Unknown University"}
            </p>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
              {uni?.country && (
                <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: "0.78rem", color: "var(--chalk-400)" }}>
                  <MapPin style={{ width: 11, height: 11 }} />
                  {uni.country}{uni.city ? `, ${uni.city}` : ""}
                </span>
              )}
              {opp.application_deadline && (
                <span style={{
                  display: "flex", alignItems: "center", gap: 5,
                  fontSize: "0.78rem",
                  color: (opp.days_until_deadline ?? 999) <= 30 ? "var(--amber)" : "var(--chalk-400)",
                }}>
                  <Clock style={{ width: 11, height: 11 }} />
                  {formatDeadline(opp.application_deadline, opp.days_until_deadline)}
                </span>
              )}
            </div>

            {/* CTA links */}
            <div style={{ display: "flex", gap: 10, marginTop: 20, flexWrap: "wrap" }}>
              {prog?.official_url && (
                <a href={prog.official_url} target="_blank" rel="noopener noreferrer"
                  className="btn-primary" style={{ fontSize: "0.78rem", padding: "8px 16px" }}>
                  <ExternalLink style={{ width: 12, height: 12 }} />
                  Official Page
                </a>
              )}
              {prog?.application_portal_url && (
                <a href={prog.application_portal_url} target="_blank" rel="noopener noreferrer"
                  className="btn-ghost" style={{ fontSize: "0.78rem", padding: "8px 16px" }}>
                  <ExternalLink style={{ width: 12, height: 12 }} />
                  Apply
                </a>
              )}
            </div>
          </div>

          {/* Right: score card */}
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
            padding: "20px 28px", flexShrink: 0,
            background: `${colPx}10`,
            border: `1px solid ${colPx}30`,
            borderRadius: "var(--r-lg)",
          }}>
            <div style={{
              fontSize: "3.4rem", fontWeight: 900, letterSpacing: "-0.06em",
              lineHeight: 1, color: col,
            }}>
              {score !== null ? Math.round(score) : "—"}
            </div>
            <div style={{ fontSize: "0.62rem", color: "var(--chalk-500)", fontWeight: 600, letterSpacing: "0.08em" }}>
              / 100
            </div>
            {opp.score_label && (
              <div style={{ fontSize: "0.68rem", fontWeight: 700, color: col, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                {opp.score_label}
              </div>
            )}
            {/* Star row */}
            <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
              {[1, 2, 3, 4, 5].map(i => {
                const filled = i <= Math.round((score ?? 0) / 20)
                return (
                  <Star key={i} style={{
                    width: 10, height: 10, color: col,
                    fill: filled ? col : "transparent",
                    opacity: filled ? 1 : 0.2,
                  }} />
                )
              })}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* ── Score breakdown ──────────────────────────────────────────── */}
      {opp.score_breakdown && (
        <GlassCard style={{ marginBottom: 14 }}>
          <SLabel>Score Breakdown</SLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
            {Object.entries(opp.score_breakdown).map(([key, val]) => {
              const pct = Math.round((val as number) * 100)
              const c   = scoreColor(pct)
              const px  = scorePx(pct)
              return (
                <div key={key}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                    <span style={{ fontSize: "0.78rem", color: "var(--chalk-300)", fontWeight: 500 }}>
                      {DIMENSION_LABELS[key] ?? key}
                    </span>
                    <span style={{ fontSize: "0.78rem", fontWeight: 700, color: c }}>{pct}%</span>
                  </div>
                  <div style={{
                    height: 4, background: "rgba(126,206,232,0.07)",
                    borderRadius: 3, overflow: "hidden",
                  }}>
                    <div style={{
                      height: "100%", width: `${pct}%`, background: c,
                      borderRadius: 3, boxShadow: `0 0 8px ${px}55`,
                      transition: "width 0.8s cubic-bezier(0.22,1,0.36,1)",
                    }} />
                  </div>
                </div>
              )
            })}
          </div>

          {opp.score_explanation && (
            <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid rgba(126,206,232,0.08)" }}>
              <SLabel>Score Explanation</SLabel>
              <pre style={{
                margin: 0, fontFamily: "inherit", fontSize: "0.8rem",
                color: "var(--chalk-300)", whiteSpace: "pre-wrap", lineHeight: 1.7,
              }}>
                {opp.score_explanation}
              </pre>
            </div>
          )}
        </GlassCard>
      )}

      {/* ── Requirements ────────────────────────────────────────────── */}
      {prog?.requirements && prog.requirements.length > 0 && (
        <GlassCard style={{ marginBottom: 14 }}>
          <SLabel>Requirements</SLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {prog.requirements.map((req, i) => (
              <div key={i} style={{
                background: "rgba(126,206,232,0.03)",
                border: "1px solid rgba(126,206,232,0.08)",
                borderRadius: "var(--r-md)",
                padding: "10px 14px",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: req.raw_text ? 5 : 0 }}>
                  <span style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--chalk-300)", textTransform: "capitalize" }}>
                    {req.requirement_type.replace(/_/g, " ")}
                  </span>
                  {req.value && (
                    <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text-primary)" }}>{req.value}</span>
                  )}
                  <span style={{
                    fontSize: "0.6rem", fontWeight: 700, padding: "2px 8px",
                    borderRadius: 999, letterSpacing: "0.06em", textTransform: "uppercase",
                    ...(req.is_strict === true
                      ? { color: "var(--rose)",  background: "rgba(212,96,112,0.10)", border: "1px solid rgba(212,96,112,0.22)" }
                      : req.is_strict === false
                      ? { color: "var(--amber)", background: "rgba(212,146,74,0.10)", border: "1px solid rgba(212,146,74,0.22)" }
                      : { color: "var(--chalk-500)", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(126,206,232,0.08)" }),
                  }}>
                    {req.is_strict === true ? "Strict" : req.is_strict === false ? "Guideline" : "Unclear"}
                  </span>
                  {req.confidence && (
                    <span style={{ marginLeft: "auto", fontSize: "0.65rem", color: "var(--chalk-600)" }}>
                      {Math.round(req.confidence * 100)}% confidence
                    </span>
                  )}
                </div>
                {req.raw_text && (
                  <p style={{ margin: 0, fontSize: "0.73rem", color: "var(--chalk-500)", fontStyle: "italic" }}>
                    &ldquo;{req.raw_text}&rdquo;
                  </p>
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* ── Application tracker ──────────────────────────────────────── */}
      <div style={{ marginBottom: 14 }}>
        <ApplicationActions opportunityId={opp.id} currentStatus={opp.application_status} />
      </div>

      {/* ── Programme details ────────────────────────────────────────── */}
      <GlassCard>
        <SLabel>Programme Details</SLabel>
        <Detail label="Degree"    value={prog?.degree_type} />
        <Detail label="Field"     value={prog?.field} />
        <Detail label="Language"  value={prog?.language} />
        <Detail label="Duration"  value={prog?.duration_months ? `${prog.duration_months} months` : null} />
        <Detail label="Tuition"   value={formatTuition(prog?.tuition_eur_per_year ?? null, prog?.is_tuition_free ?? false)} />
        <Detail label="Intake"    value={prog?.intake_months?.join(", ")} />
        {uni?.qs_rank && <Detail label="QS Rank" value={`#${uni.qs_rank}`} />}
      </GlassCard>

    </PageShell>
  )
}
