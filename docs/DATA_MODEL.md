# GuideToDream — Data Model

> Last updated: Milestone 2 (schema applied via Supabase MCP)

---

## Entity Relationship Overview

```
users (1)
  ├── profiles (1:1)           ← your academic facts
  ├── profile_preferences (1:1) ← your search preferences
  ├── opportunities (1:many)   ← scored programme+scholarship combos
  │     ├── → programmes (many:1)
  │     ├── → scholarships (many:1, optional)
  │     └── applications (1:1)  ← your pipeline status
  ├── notifications (1:many)   ← notification history
  └── (research_runs is global, not user-specific)

programmes (1)
  ├── → universities (many:1)
  └── programme_requirements (1:many)  ← each requirement has source + confidence

sources (standalone)
  ← referenced by: programme_requirements, opportunities (deadline_source_id),
                   scholarships
```

---

## Table Definitions

### `users`
The single user of this system (you).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | auto-generated |
| `email` | TEXT UNIQUE | `mahmudunmiraz@gmail.com` |
| `created_at` | TIMESTAMPTZ | auto |

---

### `profiles`
Stable academic facts. Changes rarely.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | CASCADE delete |
| `full_name` | TEXT | |
| `nationality` | TEXT | `Bangladeshi` — affects scholarship eligibility |
| `degree_level` | TEXT | `Bachelor` |
| `degree_field` | TEXT | `Computer Science` |
| `university` | TEXT | `BRAC University` |
| `graduation_year` | INTEGER | `2026` |
| `graduation_month` | INTEGER | `5` (May) |
| `is_graduated` | BOOLEAN | `false` — still in progress |
| `cgpa` | NUMERIC(4,2) | `2.80` |
| `cgpa_scale` | NUMERIC(4,2) | `4.00` |
| `english_test` | TEXT | `IELTS` |
| `english_score` | NUMERIC(4,1) | `7.0` |
| `english_test_year` | INTEGER | `2023` |
| `professional_summary` | TEXT | From CV |
| `thesis_title` | TEXT | Tree of Thoughts with CodeAct Pattern |
| `thesis_summary` | TEXT | |
| `updated_at` | TIMESTAMPTZ | auto-updates |

**Computed property** (in Python model):
```python
@property
def cgpa_normalized(self) -> float:
    return self.cgpa / self.cgpa_scale  # e.g. 2.80/4.00 = 0.70
```

---

### `profile_preferences`
Search preferences. Changes more often than academic facts.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `preferred_countries` | TEXT[] | `[Germany, Netherlands, ...]` |
| `avoided_countries` | TEXT[] | initially empty |
| `max_tuition_eur_per_year` | INTEGER | `10000` |
| `scholarship_required` | BOOLEAN | `true` |
| `stipend_preferred` | BOOLEAN | `true` |
| `degree_level_targets` | TEXT[] | `[Master]` |
| `fields_of_interest` | TEXT[] | `[AI, ML, NLP, ...]` |
| `skills` | JSONB | `{"python": "advanced", ...}` |
| `work_experience_summary` | TEXT | |
| `notable_projects` | JSONB | array of project objects |
| `notes` | TEXT | free-form notes for LLM context |

---

### `universities`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `name` | TEXT | `TU Berlin` |
| `country` | TEXT | `Germany` |
| `city` | TEXT | `Berlin` |
| `official_url` | TEXT | |
| `qs_rank` | INTEGER | nullable — unknown for many |
| `created_at` | TIMESTAMPTZ | |

---

### `programmes`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `university_id` | UUID FK → universities | |
| `name` | TEXT | `MSc Computer Science` |
| `degree_type` | TEXT | `MSc`, `MA`, `MEng` |
| `field` | TEXT | `Computer Science` |
| `language` | TEXT | `English` default |
| `duration_months` | INTEGER | typically 18 or 24 |
| `tuition_eur_per_year` | INTEGER | 0 = free |
| `tuition_notes` | TEXT | `admin fee only`, `EU/non-EU split` |
| `intake_months` | TEXT[] | `[October]`, `[September, February]` |
| `official_url` | TEXT | |
| `application_portal_url` | TEXT | |
| `status` | TEXT | `active` / `inactive` / `unverified` |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

---

### `programme_requirements`
One row per requirement. Each has its own source and confidence.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `programme_id` | UUID FK → programmes | |
| `source_id` | UUID FK → sources | nullable |
| `requirement_type` | TEXT | `cgpa_min`, `english_ielts_min`, `degree_field`, etc. |
| `value` | TEXT | `3.0`, `6.5`, `Computer Science or related` |
| `is_strict` | BOOLEAN | `true`=hard cutoff, `false`=soft, `null`=unknown |
| `confidence` | NUMERIC(3,2) | 0.00-1.00 |
| `raw_text` | TEXT | exact sentence from source page |
| `created_at` | TIMESTAMPTZ | |

**Why this table exists separately from `programmes`:**
- One programme has multiple requirements (CGPA, English, degree field, etc.)
- Each requirement has different confidence levels
- Each requirement may trace to a different source URL
- You can query: "find all programmes where cgpa_min <= 2.8 and is_strict = true"

---

### `scholarships`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `source_id` | UUID FK → sources | |
| `name` | TEXT | `DAAD Scholarship` |
| `provider` | TEXT | `DAAD`, `Erasmus+` |
| `country_scope` | TEXT[] | countries this applies to |
| `field_scope` | TEXT[] | fields this applies to |
| `nationality_scope` | TEXT[] | eligible nationalities |
| `coverage` | TEXT | `Full tuition + €850/month stipend` |
| `coverage_type` | TEXT | `full`/`partial`/`stipend_only`/`tuition_waiver`/`unknown` |
| `official_url` | TEXT | |

---

### `sources`
Every important fact traces to a source row.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `url` | TEXT | the original URL |
| `source_type` | TEXT | `university_official`, `gov_official`, `app_portal`, `edu_database`, `blog` |
| `tier` | INTEGER | 1-5 (1=most authoritative) |
| `title` | TEXT | page title |
| `raw_content_hash` | TEXT | SHA256 — changes if page content changes |
| `confidence` | NUMERIC(3,2) | |
| `retrieved_at` | TIMESTAMPTZ | when we fetched it |
| `last_verified_at` | TIMESTAMPTZ | when we last re-checked it |

**Tier meanings:**
- 1: Official university website
- 2: Official government / scholarship organization
- 3: Official application portal
- 4: Trusted educational database (DAAD, Mastersportal)
- 5: Blog / forum / social media

---

### `opportunities`
Computed entity: programme + scholarship + your eligibility + score.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `programme_id` | UUID FK → programmes | |
| `scholarship_id` | UUID FK → scholarships | nullable |
| `eligibility_status` | TEXT | `eligible`/`probably_eligible`/`uncertain`/`ineligible` |
| `eligibility_notes` | TEXT | explanation of eligibility decision |
| `total_score` | NUMERIC(5,2) | 0-100 |
| `score_breakdown` | JSONB | `{"academic_fit": 0.8, "financial_fit": 1.0, ...}` |
| `score_explanation` | TEXT | human-readable explanation |
| `application_deadline` | DATE | |
| `scholarship_deadline` | DATE | |
| `deadline_source_id` | UUID FK → sources | |
| `first_discovered_at` | TIMESTAMPTZ | |
| `last_updated_at` | TIMESTAMPTZ | |
| `is_notable_change` | BOOLEAN | true if something material changed |

---

### `applications`
Your application pipeline for a specific opportunity.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `opportunity_id` | UUID FK → opportunities | UNIQUE — one record per opportunity |
| `status` | TEXT | state machine (see below) |
| `applied_at` | DATE | when you actually submitted |
| `notes` | TEXT | your personal notes |

**Status state machine:**
```
discovered → shortlisted → preparing → applied → interview → accepted
                                               ↘ rejected
                                               ↘ withdrawn
```

---

### `notifications`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | |
| `opportunity_id` | UUID FK → opportunities | nullable |
| `notification_type` | TEXT | `new_opportunity`/`deadline_reminder`/`material_change`/`application_reminder` |
| `channel` | TEXT | `telegram`/`email`/`console` |
| `message` | TEXT | the actual message sent |
| `sent_at` | TIMESTAMPTZ | |
| `read_at` | TIMESTAMPTZ | |
| `action_taken` | TEXT | `applied`/`snoozed`/`dismissed` — user response |

---

### `research_runs`
Audit log for every research cycle.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `started_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ | |
| `status` | TEXT | `running`/`completed`/`failed`/`partial` |
| `queries_generated` | INTEGER | how many search queries were created |
| `pages_fetched` | INTEGER | how many URLs were retrieved |
| `opportunities_found` | INTEGER | new opportunities discovered |
| `opportunities_updated` | INTEGER | existing ones with changed data |
| `llm_calls` | INTEGER | total LLM API calls made |
| `llm_cost_usd` | NUMERIC(10,6) | total LLM cost |
| `search_calls` | INTEGER | total Tavily API calls |
| `errors` | JSONB | `[{"stage": "extraction", "url": "...", "error": "..."}]` |
| `notes` | TEXT | |

---

## Indexes

```sql
-- Find top opportunities for a user quickly
CREATE INDEX idx_opportunities_user_score ON opportunities(user_id, total_score DESC);

-- Find opportunities with upcoming deadlines
CREATE INDEX idx_opportunities_deadline ON opportunities(application_deadline);

-- Find active applications by status
CREATE INDEX idx_applications_user_status ON applications(user_id, status);

-- Notification history for suppression checks
CREATE INDEX idx_notifications_user_sent ON notifications(user_id, sent_at DESC);

-- Filter programmes by status
CREATE INDEX idx_programmes_status ON programmes(status);

-- Sort research runs chronologically
CREATE INDEX idx_research_runs_started ON research_runs(started_at DESC);
```
