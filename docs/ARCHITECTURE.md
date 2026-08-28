# GuideToDream — System Architecture

> Last updated: Milestone 4 complete
> Status: Active development

---

## 1. What This System Does

GuideToDream is a personal AI agent that:
1. Continuously researches European Master's programmes and scholarships
2. Evaluates them against your specific academic profile
3. Scores and ranks opportunities with transparent explanations
4. Tracks your application pipeline
5. Notifies you about deadlines and new relevant opportunities
6. Answers your questions conversationally about your opportunities

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
│                          (app/main.py)                               │
│                                                                      │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────────┐   │
│  │  REST API    │  │   Agent API     │  │   Admin / Debug      │   │
│  │  app/api/    │  │  (future)       │  │   /health endpoint   │   │
│  └──────────────┘  └─────────────────┘  └──────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                       Service Layer                             │ │
│  │                      app/services/                              │ │
│  │  ProfileService  OpportunityService  ScoringService            │ │
│  │  EligibilityService  TrackerService  NotificationService       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     Agent / AI Layer                            │ │
│  │                      app/agents/                                │ │
│  │  ExtractionAgent  DiscoveryAgent  VerificationAgent            │ │
│  │  EligibilityAgent  AssistantAgent                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                       Tool Layer                                │ │
│  │                       app/tools/                                │ │
│  │  WebSearchTool   PageFetchTool   PDFTool                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Infrastructure Layer                         │ │
│  │  PostgreSQL (Supabase)  APScheduler  structlog  google-genai   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer Responsibilities

### Tool Layer (`app/tools/`)
**Rule: Tools never call agents. Tools never call other tools.**

Tools are thin, testable wrappers over external APIs.
They have one job: call an external service and return a typed result (or raise a typed ToolError).

| File | Responsibility | External Dependency |
|------|---------------|---------------------|
| `tools/base.py` | Shared types: `SearchResult`, `PageContent`, `PDFContent`, `ToolError`, `ToolErrorType` | None |
| `tools/web_search.py` | Search the web, return structured results | Tavily API |
| `tools/page_fetch.py` | Fetch a URL, return clean Markdown; handle PDFs | httpx, BeautifulSoup, PyMuPDF, Playwright (optional) |

### Agent Layer (`app/agents/`)
**Rule: Agents call tools and the LLM utility. Agents never touch the database directly.**

Agents contain AI reasoning. They use LLMs for tasks that require interpreting
ambiguous language. They do NOT use LLMs for things deterministic code can handle.

| File | Responsibility | Calls |
|------|---------------|-------|
| `agents/extraction_agent.py` | Extract structured programme/scholarship data from page Markdown | `utils/llm.py` |
| `agents/discovery_agent.py` *(planned)* | Generate search queries from user profile | `utils/llm.py`, `tools/web_search.py` |
| `agents/verification_agent.py` *(planned)* | Cross-check extracted facts against official sources | `utils/llm.py`, `tools/page_fetch.py` |
| `agents/assistant_agent.py` *(planned)* | Conversational interface over stored opportunities | `utils/llm.py` |

### Service Layer (`app/services/`)
**Rule: Services contain deterministic business logic. Services call agents when AI is needed.**

Services orchestrate the system. They read/write the database,
call agents for AI tasks, and implement business rules in plain Python.

| File | Responsibility |
|------|---------------|
| `services/profile_service.py` *(planned)* | Read/update user profile and preferences |
| `services/opportunity_service.py` *(planned)* | Store, retrieve, deduplicate opportunities |
| `services/eligibility_service.py` *(planned)* | Apply hard/soft eligibility rules against profile |
| `services/scoring_service.py` *(planned)* | Calculate weighted opportunity score + explanation |
| `services/tracking_service.py` *(planned)* | Manage application pipeline state transitions |
| `services/notification_service.py` *(planned)* | Decide when/what to notify; send via Telegram/email |
| `services/change_detector.py` *(planned)* | Diff new extraction against stored data; flag changes |

### Infrastructure Layer
| File | Responsibility |
|------|---------------|
| `app/config.py` | Load all settings from environment variables (fail-fast if missing) |
| `app/database.py` | SQLAlchemy async engine, session factory, `get_db()` dependency |
| `app/main.py` | FastAPI app creation, lifespan hooks, router registration |
| `app/utils/llm.py` | Unified LLM call wrapper (google-genai SDK, cost logging) |
| `app/utils/logging.py` | structlog setup, sensitive field filtering |
| `alembic/env.py` | Database migration environment (reads sync DB URL) |

---

## 4. Data Flow: Full Research Cycle

This is the complete journey from "scheduled trigger" to "notification sent":

```
TRIGGER (scheduled job or manual API call)
    │
    ▼
ResearchOrchestrator.run()          [services/research_orchestrator.py - planned]
    │
    ├─► 1. Load profile              ProfileService.get_profile()
    │         └─► reads: users, profiles, profile_preferences tables
    │
    ├─► 2. Generate search queries   DiscoveryAgent.generate_queries(profile)
    │         └─► calls: LLM (fast model)
    │         └─► returns: ["MSc AI Germany free tuition 2025", ...]
    │
    ├─► 3. Execute searches          WebSearchTool.search_web(query)
    │         └─► calls: Tavily API
    │         └─► returns: SearchResponse (list of URLs + snippets)
    │
    ├─► 4. Deduplicate URLs          ChangeDetector.filter_known_urls(urls)
    │         └─► reads: sources table
    │         └─► skips: already-visited URLs with unchanged content hash
    │
    ├─► 5. Fetch pages               PageFetchTool.fetch_page(url)
    │         └─► calls: httpx (static) or Playwright (dynamic)
    │         └─► returns: PageContent (clean Markdown)
    │
    ├─► 6. Extract information       ExtractionAgent.extract_programme(markdown, url)
    │         └─► calls: LLM (fast model)
    │         └─► returns: ExtractedProgramme (validated Pydantic object)
    │
    ├─► 7. Save source record        OpportunityService.save_source(url, content_hash)
    │         └─► writes: sources table
    │
    ├─► 8. Check eligibility         EligibilityService.evaluate(programme, profile)
    │         └─► deterministic: CGPA cutoff, English requirement, citizenship
    │         └─► returns: EligibilityResult (eligible/probably/uncertain/ineligible)
    │
    ├─► 9. Score opportunity         ScoringService.score(programme, profile)
    │         └─► deterministic: weighted dimensions
    │         └─► returns: ScoreResult (0-100 + breakdown + explanation)
    │
    ├─► 10. Detect changes           ChangeDetector.diff(new_extraction, stored)
    │         └─► reads: programmes, opportunities tables
    │         └─► flags: deadline changed, tuition changed, scholarship added
    │
    ├─► 11. Persist to database      OpportunityService.upsert(opportunity)
    │         └─► writes: universities, programmes, programme_requirements,
    │                     opportunities, applications tables
    │
    ├─► 12. Log research run         ResearchRun record updated
    │         └─► writes: research_runs table (cost, errors, counts)
    │
    └─► 13. Evaluate notifications   NotificationService.evaluate(opportunity)
              └─► reads: notifications table (suppression check)
              └─► sends: Telegram bot message or email
              └─► writes: notifications table
```

---

## 5. Configuration Flow

```
.env file (local) or environment variables (deployed)
    │
    ▼
app/config.py  (pydantic-settings reads and validates all vars)
    │
    ├─► get_settings()  [cached singleton, call anywhere]
    │
    ├─► app/database.py  reads: DATABASE_URL, DATABASE_URL_SYNC
    ├─► app/utils/llm.py  reads: GEMINI_API_KEY, LLM_FAST_MODEL, LLM_SMART_MODEL
    ├─► app/tools/web_search.py  reads: TAVILY_API_KEY
    ├─► app/tools/page_fetch.py  reads: PLAYWRIGHT_ENABLED, request_timeout_seconds
    └─► app/services/notification_service.py  reads: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

**Why this matters:** Every part of the app reads config through `get_settings()`.
There is no other way to get configuration. If an env var is missing,
the app crashes at startup with a clear message — never silently mid-operation.

---

## 6. Database Schema Overview

See `docs/DATA_MODEL.md` for full schema. Tables and their roles:

| Table | Role |
|-------|------|
| `users` | Single user (you). FK anchor for all personal data |
| `profiles` | Academic facts: degree, CGPA, English score |
| `profile_preferences` | Search preferences: target countries, budget, interests |
| `universities` | University entities (shared across programmes) |
| `programmes` | Individual Master's programmes |
| `programme_requirements` | Per-field requirements with confidence + is_strict |
| `scholarships` | Scholarship entities (can apply to many programmes) |
| `sources` | Every URL fetched, with content hash for change detection |
| `opportunities` | Computed: programme + scholarship + eligibility + score |
| `applications` | Application pipeline state (discovered → applied → accepted) |
| `notifications` | Log of every notification sent (used for suppression) |
| `research_runs` | Audit log: every research cycle with cost and error tracking |

---

## 7. LLM Usage Policy

**Use LLM for:**
- Generating search queries from user profile (`DiscoveryAgent`)
- Extracting structured data from unstructured page text (`ExtractionAgent`)
- Interpreting ambiguous admission requirement language (`EligibilityAgent`)
- Explaining why an opportunity matches the user (`ScoringService`)
- Answering conversational questions (`AssistantAgent`)

**Never use LLM for:**
- Date arithmetic (deadline passed? days remaining?)
- Numerical comparisons (CGPA >= minimum? Tuition <= budget?)
- Database queries (find all programmes in Germany)
- Status transitions (mark application as "applied")
- Duplicate detection (is this URL already in the database?)
- Sending notifications

---

## 8. Error Handling Philosophy

Every failure mode is handled explicitly. The system never silently swallows errors.

| Layer | Error type | Handling |
|-------|-----------|---------|
| Tools | `ToolError` with `retryable` flag | Retry if transient, fail fast if permanent |
| Agents | LLM returns bad JSON | Log + return empty result, pipeline continues |
| Agents | LLM call fails | Log + return empty result with note, never crash pipeline |
| Services | DB connection fails | Raise, let orchestrator log to `research_runs.errors` |
| Services | Eligibility uncertain | Return `UNCERTAIN` status, flag for manual review |
| Orchestrator | Any stage fails | Log error, continue to next URL, record in `research_runs` |

---

## 9. Milestone Progress

| Milestone | Status | Description |
|-----------|--------|-------------|
| M1 | ✅ Done | Discovery + Architecture phase |
| M2 | ✅ Done | Repo setup, config, database, profile model |
| M3 | ✅ Done | Web research tools (search, fetch, PDF) |
| M4 | ✅ Done | Information extraction agent (Gemini LLM) |
| M5 | ✅ Done | Eligibility engine (hard rules + soft interpretation) |
| M6 | ✅ Done | Scoring engine (weighted dimensions + explanation) |
| M7 | ✅ Done | Full research pipeline (orchestrated end-to-end) |
| M8 | ✅ Done | Application tracker + conversational assistant |
| M9 | ✅ Done | Telegram notifications |
| M10 | 🔄 Next | Scheduling + continuous research |
| M11 | ⏳ | Observability + LLM cost dashboard |
| M12 | ⏳ | Deployment (Render/Fly.io) + CI/CD |
| M13 | ⏳ | MCP server (Claude Desktop integration) |
