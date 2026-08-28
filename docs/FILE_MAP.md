# GuideToDream — File Connection Map

> This document answers: "What does this file do, what does it import, and what imports it?"
> Updated as new files are added. Last updated: Milestone 4.

---

## How to Read This Document

Each file entry shows:
- **Purpose**: what it does in one sentence
- **Imports from**: what it depends on
- **Imported by**: what depends on it
- **Triggers**: what happens when this file's code runs

---

## Configuration & Infrastructure

### `app/config.py`
**Purpose:** Reads all environment variables, validates them, exposes a cached `get_settings()` singleton.

**Imports from:**
- `pydantic_settings` (third-party)
- `.env` file (via python-dotenv, loaded automatically)

**Imported by:**
- `app/database.py` → reads DATABASE_URL
- `app/utils/llm.py` → reads GEMINI_API_KEY, LLM_FAST_MODEL, LLM_SMART_MODEL
- `app/tools/web_search.py` → reads TAVILY_API_KEY
- `app/tools/page_fetch.py` → reads PLAYWRIGHT_ENABLED, request_timeout_seconds
- `app/main.py` → reads APP_ENV, LOG_LEVEL

**Triggers:** If any required env var is missing → app crashes at startup with a clear message.

---

### `app/database.py`
**Purpose:** Creates the SQLAlchemy async engine and session factory. Provides `get_db()` FastAPI dependency.

**Imports from:**
- `app/config.py` → get_settings() for DATABASE_URL
- `sqlalchemy.ext.asyncio` (third-party)

**Imported by:**
- `app/models/*.py` → all models inherit from `Base` defined here
- `alembic/env.py` → imports `Base` to discover all tables for migrations
- All future service files → use `get_db()` to get a session

**Triggers:**
- On import → creates the connection pool to Supabase PostgreSQL
- `get_db()` called → opens a session, yields it, closes it after the request

---

### `app/main.py`
**Purpose:** FastAPI application entry point. Creates the app, registers routes, runs startup/shutdown logic.

**Imports from:**
- `app/config.py` → get_settings()
- `app/utils/logging.py` → setup_logging()
- `fastapi` (third-party)

**Imported by:**
- `uvicorn` (the web server) → `uvicorn app.main:app --reload`

**Triggers:**
- On startup (lifespan) → initializes logging, future: starts scheduler
- On shutdown → cleanup

---

### `app/utils/logging.py`
**Purpose:** Configures structlog for structured JSON logging. Filters sensitive fields.

**Imports from:**
- `structlog` (third-party)

**Imported by:**
- `app/main.py` → calls `setup_logging()` once at startup
- All other files → call `structlog.get_logger(__name__)` to get a logger

**Triggers:** Every `logger.info()`, `logger.error()` etc. call runs through this pipeline, adding timestamps, log level, filename, and redacting sensitive fields.

---

### `app/utils/llm.py`
**Purpose:** Unified wrapper for all LLM calls. Handles auth, error classification, cost logging.

**Imports from:**
- `app/config.py` → get_settings() for API key and model names
- `google.genai` (third-party, google-genai SDK)
- `structlog` (third-party)

**Imported by:**
- `app/agents/extraction_agent.py` → `call_llm()` for programme/scholarship extraction
- Future agents → all LLM calls go through here

**Triggers:**
1. Caller invokes `call_llm(prompt, model="fast")`
2. Reads GEMINI_API_KEY from config
3. Calls Gemini API
4. Logs token usage and elapsed time
5. Returns text response or raises `LLMError`

---

## Tools

### `app/tools/base.py`
**Purpose:** Shared data types and exceptions for all tools.

**Imports from:** `dataclasses`, `datetime` (stdlib only)

**Imported by:**
- `app/tools/web_search.py` → uses `SearchResult`, `SearchResponse`, `ToolError`, `ToolErrorType`
- `app/tools/page_fetch.py` → uses `PageContent`, `PDFContent`, `ToolError`, `ToolErrorType`
- `app/tools/__init__.py` → re-exports all types
- Future agents/services → catch `ToolError` to handle failures

---

### `app/tools/web_search.py`
**Purpose:** Search the web using Tavily API. Returns structured `SearchResponse`.

**Imports from:**
- `app/config.py` → reads TAVILY_API_KEY
- `app/tools/base.py` → `SearchResult`, `SearchResponse`, `ToolError`, `ToolErrorType`
- `tavily` (third-party)
- `tenacity` (third-party, retry logic)
- `structlog`

**Imported by:**
- `app/tools/__init__.py` → re-exports `search_web`
- Future `app/agents/discovery_agent.py` → calls `search_web(query)` to find programme URLs

**Triggers:**
1. Agent calls `search_web("MSc AI Germany free tuition")`
2. Validates query, calls Tavily API
3. On rate limit: waits and retries up to 3 times (exponential backoff)
4. Returns `SearchResponse` with list of `SearchResult` objects
5. On permanent failure: raises `ToolError(retryable=False)`

---

### `app/tools/page_fetch.py`
**Purpose:** Fetch a URL and return clean Markdown. Auto-detects PDFs. Optional Playwright for JS pages.

**Imports from:**
- `app/config.py` → reads PLAYWRIGHT_ENABLED, request_timeout_seconds
- `app/tools/base.py` → `PageContent`, `PDFContent`, `ToolError`, `ToolErrorType`
- `httpx` (third-party, async HTTP client)
- `beautifulsoup4` + `lxml` (third-party, HTML parsing)
- `fitz` / `pymupdf` (third-party, PDF extraction)
- `playwright` (third-party, optional — only if PLAYWRIGHT_ENABLED=true)
- `tenacity` (third-party, retry logic)

**Imported by:**
- `app/tools/__init__.py` → re-exports `fetch_page`, `fetch_page_rendered`, `fetch_pdf`
- Future `app/agents/discovery_agent.py` → fetches programme pages
- Future `app/agents/verification_agent.py` → re-fetches pages to verify facts

**Triggers (fetch_page):**
1. Agent calls `fetch_page("https://university.edu/msc-cs")`
2. Checks if domain is known-blocked
3. Makes HTTP GET request with browser-like headers
4. On timeout/connection error: retries up to 3 times
5. On 404: raises `ToolError(NOT_FOUND, retryable=False)`
6. Detects if response is PDF → routes to `fetch_pdf_bytes()`
7. Converts HTML to Markdown via BeautifulSoup
8. Returns `PageContent(url, title, markdown, word_count, ...)`

---

## Agents

### `app/agents/extraction_agent.py`
**Purpose:** Takes page Markdown, calls Gemini LLM, returns structured `ExtractedProgramme` or `ExtractedScholarship`.

**Imports from:**
- `app/utils/llm.py` → `call_llm()`, `LLMError`
- `pydantic` (third-party, output schema validation)
- `structlog`

**Imported by:**
- Future `app/services/research_orchestrator.py` → called after each page is fetched
- `tests/unit/test_extraction.py` → unit tests

**Triggers:**
1. Orchestrator calls `extract_programme(markdown, url)`
2. Truncates content to 8000 chars (cost control)
3. Builds prompt (schema + rules + content)
4. Calls `call_llm(prompt, model="fast", temperature=0.1)`
5. Strips markdown fences from response, parses JSON
6. Validates against `ExtractedProgramme` Pydantic model
7. If parse fails → logs error, returns empty `ExtractedProgramme(confidence=0.0)`
8. Returns validated `ExtractedProgramme` with requirements, confidence, evidence

---

## Models (Database Tables)

### `app/models/user.py`
**Table:** `users`
**Imported by:** `app/models/__init__.py`, `alembic/env.py`
**Relationships:** one User → one Profile, one ProfilePreferences, many Opportunities, many Applications, many Notifications

### `app/models/profile.py`
**Tables:** `profiles`, `profile_preferences`
**Imported by:** `app/models/__init__.py`, future `ProfileService`
**Key fields:** `cgpa`, `cgpa_scale`, `english_score`, `preferred_countries`, `max_tuition_eur_per_year`

### `app/models/programme.py`
**Tables:** `universities`, `programmes`, `programme_requirements`
**Imported by:** `app/models/__init__.py`, future `OpportunityService`
**Key design:** `programme_requirements` stores one row per requirement, with `is_strict`, `confidence`, `raw_text` — so each requirement has its own evidence trail

### `app/models/source.py`
**Table:** `sources`
**Imported by:** `app/models/__init__.py`, future services
**Key field:** `raw_content_hash` (SHA256) — if this changes on re-fetch, something on the page changed

### `app/models/opportunity.py`
**Table:** `opportunities`
**Imported by:** `app/models/__init__.py`
**Key design:** Computed/derived entity. Joins programme + scholarship + eligibility result + score. The same programme can be two opportunities if paired with different scholarships.

### `app/models/application.py`
**Table:** `applications`
**Imported by:** `app/models/__init__.py`
**Key design:** State machine: `discovered → shortlisted → preparing → applied → interview → accepted/rejected/withdrawn`

### `app/models/notification.py`
**Table:** `notifications`
**Imported by:** `app/models/__init__.py`
**Key design:** Every notification logged here. `NotificationService` queries this table before sending to prevent spam (suppression window).

### `app/models/research.py`
**Table:** `research_runs`
**Imported by:** `app/models/__init__.py`
**Key design:** Audit log. Every research cycle creates one row. Records LLM cost, pages fetched, errors. This is how you know what the agent did at 3am.

### `app/models/__init__.py`
**Purpose:** Imports ALL models. This single import is what makes Alembic see all tables.
**Critical rule:** If you add a new model file and forget to import it here, Alembic will never create its table.

---

## Database Migrations

### `alembic/env.py`
**Purpose:** Tells Alembic how to connect to the database and which models to track.

**Imports from:**
- `app/config.py` → reads DATABASE_URL_SYNC (psycopg2 driver — Alembic is sync)
- `app/database.py` → imports `Base` (which has all table metadata)
- `app/models` → imports all models (via `import app.models`)

**Triggered by:**
```bash
python -m alembic revision --autogenerate -m "description"
python -m alembic upgrade head
```

**Flow:**
1. Alembic reads `alembic.ini` → finds `script_location = alembic`
2. Runs `alembic/env.py`
3. `env.py` connects to DB via `DATABASE_URL_SYNC`
4. Compares `Base.metadata` (your Python models) against actual DB schema
5. Generates a migration file in `alembic/versions/`
6. `upgrade head` applies all pending migrations

**Note:** In this project, the initial schema was applied directly via Supabase MCP (`mcp_supabase_apply_migration`). Alembic tracks future changes.

---

## Seed Script

### `scripts/seed_profile.py`
**Purpose:** One-time script to insert your personal profile into the database.

**Imports from:**
- `app/database.py` → `AsyncSessionLocal`
- `app/models` → `User`, `Profile`, `ProfilePreferences`
- `sqlalchemy` → `select`

**Triggered by:**
```bash
python scripts/seed_profile.py
```

**Flow:**
1. Opens async DB session
2. Checks if user with your email already exists
3. If not: creates User record
4. Creates/updates Profile with academic data
5. Creates/updates ProfilePreferences with target countries, budget, interests
6. Commits all in one transaction

**Note:** Idempotent — safe to run multiple times. Re-running updates existing data.

---

## Tests

### `tests/unit/test_tools.py`
**Tests:** `_html_to_markdown()`, `_compute_hash()`, `ToolError` construction
**Does NOT test:** Real HTTP requests, real Tavily API calls
**Run with:** `python -m pytest tests/unit/test_tools.py -v`

### `tests/unit/test_extraction.py`
**Tests:** `_extract_json()`, `ExtractedProgramme` validation, `ExtractedScholarship` validation
**Does NOT test:** Real Gemini API calls (those are integration tests)
**Run with:** `python -m pytest tests/unit/test_extraction.py -v`

---

## Planned Files (Not Yet Created)

| File | Will do |
|------|---------|
| `app/services/eligibility_service.py` | Hard/soft eligibility rules against user profile |
| `app/services/scoring_service.py` | Weighted 8-dimension score with explanation |
| `app/services/opportunity_service.py` | DB persistence for opportunities, deduplication |
| `app/services/research_orchestrator.py` | Coordinates a full research cycle (M7) |
| `app/services/notification_service.py` | Decides what to notify, suppression logic (M9) |
| `app/agents/discovery_agent.py` | Generates search queries from profile (M7) |
| `app/agents/verification_agent.py` | Cross-checks facts against official sources (M7) |
| `app/agents/assistant_agent.py` | Conversational interface over opportunities (M8) |
| `app/api/profile.py` | REST API for profile read/update |
| `app/api/opportunities.py` | REST API for opportunity listing and filtering |
| `app/api/applications.py` | REST API for application tracker |
| `app/scheduler/jobs.py` | APScheduler jobs for automated research cycles (M10) |
| `app/mcp/server.py` | MCP server definition for Claude Desktop (M13) |
