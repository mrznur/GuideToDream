/**
 * lib/api.ts
 * ----------
 * Typed API client for the GuideToDream backend.
 * All components import from here — never fetch() directly.
 * Swap the BASE_URL to point at localhost during development.
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://guidetodream.onrender.com";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    next: { revalidate: 60 }, // cache for 60s (Next.js ISR)
  });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

async function patch<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`PATCH ${path} → ${res.status}`);
  return res.json();
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface QuickStats {
  total_opportunities: number;
  eligible_opportunities: number;
  deadlines_in_30_days: number;
  last_research_run: string | null;
  last_run_status: string | null;
  scheduler_running: boolean;
}

export interface SchedulerJob {
  id: string;
  name: string;
  next_run: string | null;
}

export interface DashboardHealth {
  database: string;
  llm_configured: boolean;
  search_configured: boolean;
  telegram_enabled: boolean;
  scheduler_running: boolean;
  scheduler_jobs: SchedulerJob[];
}

export interface CostSummary {
  total_llm_cost_usd: number;
  avg_cost_per_run_usd: number;
  total_pages_fetched: number;
  total_opportunities_found: number;
  runs_completed: number;
  runs_with_errors: number;
}

export interface Dashboard {
  generated_at: string;
  health: DashboardHealth;
  opportunities: {
    total: number;
    by_eligibility: Record<string, number>;
    by_score_band: Record<string, number>;
    free_tuition_count: number;
    with_deadline_count: number;
  };
  costs: CostSummary;
  notifications: { total_sent: number; by_type: Record<string, number> };
  recent_runs: ResearchRun[];
  last_research_run: ResearchRun | null;
}

export interface Requirement {
  requirement_type: string;
  value: string | null;
  is_strict: boolean | null;
  confidence: number | null;
  raw_text: string | null;
}

export interface Programme {
  id: string;
  name: string;
  degree_type: string;
  field: string;
  language: string;
  duration_months: number | null;
  tuition_eur_per_year: number | null;
  tuition_notes: string | null;
  is_tuition_free: boolean;
  intake_months: string[];
  official_url: string | null;
  application_portal_url: string | null;
  status: string;
  requirements: Requirement[];
}

export interface University {
  id: string;
  name: string;
  country: string;
  city: string | null;
  official_url: string | null;
  qs_rank: number | null;
}

export interface Opportunity {
  id: string;
  eligibility_status: string;
  eligibility_notes: string | null;
  total_score: number | null;
  score_breakdown: Record<string, number> | null;
  score_explanation: string | null;
  score_label: string | null;
  application_deadline: string | null;
  scholarship_deadline: string | null;
  days_until_deadline: number | null;
  first_discovered_at: string;
  last_updated_at: string;
  is_notable_change: boolean;
  programme: Programme | null;
  university: University | null;
  application_status: string | null;
}

export interface OpportunityList {
  items: Opportunity[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface Application {
  id: string;
  opportunity_id: string;
  status: string;
  applied_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PipelineSummary {
  pipeline: Record<string, { count: number; opportunity_ids: string[] }>;
  total: number;
  active: number;
}

export interface ResearchRun {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  queries_generated: number;
  pages_fetched: number;
  opportunities_found: number;
  opportunities_updated: number;
  llm_calls: number;
  llm_cost_usd: number;
  search_calls: number;
  errors: Array<{ stage: string; url?: string; error: string }>;
  duration_seconds: number | null;
}

// ─── API calls ────────────────────────────────────────────────────────────────

export const api = {
  // Admin
  getStats: () => get<QuickStats>("/api/v1/admin/stats"),
  getDashboard: () => get<Dashboard>("/api/v1/admin/dashboard"),
  getRuns: (limit = 20) => get<ResearchRun[]>(`/api/v1/admin/runs?limit=${limit}`),

  // Opportunities
  getOpportunities: (params?: {
    eligibility?: string;
    min_score?: number;
    sort_by?: string;
    page?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.eligibility) q.set("eligibility", params.eligibility);
    if (params?.min_score) q.set("min_score", String(params.min_score));
    if (params?.sort_by) q.set("sort_by", params.sort_by);
    if (params?.page) q.set("page", String(params.page));
    return get<OpportunityList>(`/api/v1/opportunities?${q}`);
  },
  getTopOpportunities: (limit = 10) =>
    get<Opportunity[]>(`/api/v1/opportunities/top?limit=${limit}`),
  getUpcomingDeadlines: (days = 30) =>
    get<Opportunity[]>(`/api/v1/opportunities/deadlines?within_days=${days}`),
  getOpportunity: (id: string) => get<Opportunity>(`/api/v1/opportunities/${id}`),

  // Applications
  getApplications: (status?: string) =>
    get<Application[]>(`/api/v1/applications${status ? `?status=${status}` : ""}`),
  getPipeline: () => get<PipelineSummary>("/api/v1/applications/pipeline"),
  transitionStatus: (id: string, newStatus: string, notes?: string) =>
    patch<Application>(`/api/v1/applications/${id}/status`, {
      new_status: newStatus,
      notes,
    }),
  createApplication: (opportunityId: string) =>
    post<Application>("/api/v1/applications", { opportunity_id: opportunityId }),

  // Assistant
  ask: (question: string) =>
    post<{ question: string; answer: string }>("/api/v1/assistant/ask", {
      question,
    }),

  // Research
  triggerResearch: () => post("/api/v1/schedule/trigger/research"),
  getScheduleStatus: () => get("/api/v1/schedule/status"),
};
