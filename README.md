# GuideToDream

A personal AI agent that continuously researches European Master's programmes
and scholarships, evaluates them against your academic profile, and keeps you
informed about the best opportunities.

Built as a learning project to understand modern AI engineering: agents, MCP,
RAG, LLMs, async Python, and production software practices.

---

## Features (in progress)

- [x] Structured academic profile storage
- [x] PostgreSQL database with full schema
- [ ] Web research pipeline (Tavily + httpx + Playwright)
- [ ] LLM-powered information extraction (Gemini)
- [ ] Eligibility engine (hard rules + soft interpretation)
- [ ] Opportunity scoring with transparent explanations
- [ ] Application pipeline tracker
- [ ] Telegram notifications
- [ ] Conversational assistant
- [ ] Scheduled continuous research

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Package manager | uv |
| Web framework | FastAPI |
| Database | PostgreSQL (Supabase) |
| ORM | SQLAlchemy 2.x async |
| Migrations | Alembic |
| LLM | Google Gemini (free tier) via LiteLLM |
| Web search | Tavily (free tier) |
| Page fetching | httpx + BeautifulSoup + Playwright |
| Scheduling | APScheduler |
| Logging | structlog |
| Notifications | Telegram Bot API |

---

## Setup

### 1. Prerequisites

- Python 3.12+
- Git
- A [Supabase](https://supabase.com) account (free)
- A [Google AI Studio](https://aistudio.google.com) API key (free)
- A [Tavily](https://tavily.com) API key (free tier)

### 2. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/GuideToDream.git
cd GuideToDream
python -m uv sync --extra dev
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual values
```

Required variables:
- `DATABASE_URL` — Supabase async connection string
- `DATABASE_URL_SYNC` — Supabase sync connection string (for Alembic)
- `GEMINI_API_KEY` — Google Gemini API key

### 4. Run database migrations

```bash
python -m alembic upgrade head
```

### 5. Seed your profile

```bash
python scripts/seed_profile.py
```

### 6. Run the development server

```bash
python -m uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

---

## Development

### Run tests
```bash
python -m pytest
```

### Lint and format
```bash
python -m ruff check .
python -m ruff format .
```

### Type check
```bash
python -m mypy app/
```

### Create a new migration after changing models
```bash
python -m alembic revision --autogenerate -m "describe your change"
python -m alembic upgrade head
```

---

## Project Structure

```
GuideToDream/
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── config.py        # Settings from environment variables
│   ├── database.py      # SQLAlchemy engine and session
│   ├── models/          # Database models (ORM)
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic (deterministic)
│   ├── agents/          # LLM-powered components
│   ├── tools/           # MCP tool implementations
│   ├── api/             # FastAPI route handlers
│   └── utils/           # Logging, helpers
├── alembic/             # Database migrations
├── tests/               # Unit and integration tests
├── scripts/             # One-time setup scripts
└── docs/                # Architecture and design docs
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full system design.

---

## License

Personal project — not licensed for redistribution.
