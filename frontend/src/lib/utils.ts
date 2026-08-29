import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatScore(score: number | null): string {
  if (score === null) return "—"
  return `${Math.round(score)}`
}

export function scoreColor(score: number | null): string {
  if (score === null) return "text-zinc-500"
  if (score >= 90) return "text-emerald-400"
  if (score >= 75) return "text-blue-400"
  if (score >= 60) return "text-yellow-400"
  if (score >= 45) return "text-orange-400"
  return "text-red-400"
}

export function scoreBg(score: number | null): string {
  if (score === null) return "bg-zinc-800"
  if (score >= 90) return "bg-emerald-500/10 border-emerald-500/30"
  if (score >= 75) return "bg-blue-500/10 border-blue-500/30"
  if (score >= 60) return "bg-yellow-500/10 border-yellow-500/30"
  if (score >= 45) return "bg-orange-500/10 border-orange-500/30"
  return "bg-red-500/10 border-red-500/30"
}

export function eligibilityColor(status: string): string {
  switch (status) {
    case "eligible": return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
    case "probably_eligible": return "text-blue-400 bg-blue-500/10 border-blue-500/30"
    case "uncertain": return "text-yellow-400 bg-yellow-500/10 border-yellow-500/30"
    case "ineligible": return "text-red-400 bg-red-500/10 border-red-500/30"
    default: return "text-zinc-400 bg-zinc-500/10 border-zinc-500/30"
  }
}

export function eligibilityLabel(status: string): string {
  switch (status) {
    case "eligible": return "Eligible"
    case "probably_eligible": return "Probably Eligible"
    case "uncertain": return "Uncertain"
    case "ineligible": return "Ineligible"
    default: return status
  }
}

export function formatDeadline(deadline: string | null, daysLeft: number | null): string {
  if (!deadline) return "No deadline"
  const d = new Date(deadline)
  const formatted = d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
  if (daysLeft === null) return formatted
  if (daysLeft < 0) return `${formatted} (passed)`
  if (daysLeft === 0) return `${formatted} (today!)`
  if (daysLeft <= 7) return `${formatted} (${daysLeft}d — urgent)`
  if (daysLeft <= 30) return `${formatted} (${daysLeft}d left)`
  return `${formatted} (${daysLeft}d)`
}

export function formatTuition(eur: number | null, isFree: boolean): string {
  if (isFree || eur === 0) return "Free"
  if (eur === null) return "Unknown"
  if (eur < 1000) return `€${eur}/yr`
  return `€${(eur / 1000).toFixed(0)}k/yr`
}

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}
