"""
app/api/admin.py
─────────────────
Admin / observability endpoints.

PERFORMANCE: The dashboard runs all independent DB queries concurrently
with asyncio.gather — previously they were sequential (6+ round trips).
Now it's a single logical "wave" of queries.
"""

import asyncio
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.notification import Notification
from app.models.opportunity import Opportunity
from app.models.programme import Programme
from app.models.research import ResearchRun
from app.models.user import User
from app.scheduler.jobs import scheduler

router = APIRouter(prefix="/admin", tags=["admin"])

_USER_EMAIL: str = get_settings().user_email


# ─── Helpers ──────────────────────────────────────────────────────────────

async def _get_user_id(db: AsyncSession, email: str) -> str | None:
    r = await db.execute(select(User.id).where(User.email == email))
    row = r.scalar_one_or_none()
    return str(row) if row else None


async def _db_health(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _get_runs(db: AsyncSession, limit: int) -> list:
    r = await db.execute(
        select(ResearchRun).order_by(desc(ResearchRun.started_at)).limit(limit)
    )
    return r.scalars().all()


async def _opp_stats(db: AsyncSession, user_id: str) -> dict:
    """Aggregate opportunity stats using DB-level queries, not Python loops."""
    uid = user_id  # shorthand

    # All counts in one gather
    (
        total_r,
        free_r,
        deadline_r,
        elig_r,
    ) = await asyncio.gather(
        db.execute(
            select(func.count(Opportunity.id))
            .where(Opportunity.user_id == uid)
        ),
        db.execute(
            select(func.count(Opportunity.id))
            .join(Programme, Programme.id == Opportunity.programme_id)
            .where(Opportunity.user_id == uid)
            .where(Programme.tuition_eur_per_year == 0)
        ),
        db.execute(
            select(func.count(Opportunity.id))
            .where(Opportunity.user_id == uid)
            .where(Opportunity.application_deadline.isnot(None))
        ),
        # Per-eligibility counts
        db.execute(
            select(Opportunity.eligibility_status, func.count(Opportunity.id))
            .where(Opportunity.user_id == uid)
            .group_by(Opportunity.eligibility_status)
        ),
    )

    by_eligibility = {row[0]: row[1] for row in elig_r.all()}

    # Score bands — one query with CASE-style grouping via Python after a lean select
    scores_r = await db.execute(
        select(Opportunity.total_score)
        .where(Opportunity.user_id == uid)
        .where(Opportunity.total_score.isnot(None))
    )
    scores = [float(s) for (s,) in scores_r.all()]
    bands = {
        "exceptional_90_plus": sum(1 for s in scores if s >= 90),
        "strong_75_89":        sum(1 for s in scores if 75 <= s < 90),
        "good_60_74":          sum(1 for s in scores if 60 <= s < 75),
        "moderate_45_59":      sum(1 for s in scores if 45 <= s < 60),
        "weak_below_45":       sum(1 for s in scores if s < 45),
    }

    return {
        "total":              total_r.scalar() or 0,
        "free_tuition_count": free_r.scalar() or 0,
        "with_deadline_count": deadline_r.scalar() or 0,
        "by_eligibility":     by_eligibility,
        "by_score_band":      bands,
    }


async def _notif_stats(db: AsyncSession, user_id: str) -> dict:
    r = await db.execute(
        select(Notification.notification_type, func.count(Notification.id))
        .where(Notification.user_id == user_id)
        .where(Notification.sent_at.isnot(None))
        .group_by(Notification.notification_type)
    )
    rows = r.all()
    by_type = {row[0]: row[1] for row in rows}
    return {"total_sent": sum(by_type.values()), "by_type": by_type}


# ─── Dashboard ────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Full observability dashboard.
    All independent queries run concurrently — fast even on cold starts.
    """
    settings = get_settings()

    # Wave 1: things that don't need user_id
    db_ok, runs, user_id = await asyncio.gather(
        _db_health(db),
        _get_runs(db, limit=10),
        _get_user_id(db, _USER_EMAIL),
    )

    # Build health block (synchronous, no DB)
    health = {
        "database":         "connected" if db_ok else "error",
        "llm_configured":   bool(settings.gemini_api_key),
        "search_configured": bool(settings.tavily_api_key),
        "telegram_enabled": settings.telegram_enabled,
        "scheduler_running": scheduler.running,
        "scheduler_jobs": [
            {
                "id":       job.id,
                "name":     job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            }
            for job in scheduler.get_jobs()
        ],
    }

    # Build run history (synchronous processing)
    run_history = []
    total_cost = 0.0
    total_pages = 0
    total_found = 0
    for run in runs:
        cost = float(run.llm_cost_usd or 0)
        total_cost  += cost
        total_pages += run.pages_fetched or 0
        total_found += run.opportunities_found or 0
        duration = None
        if run.completed_at and run.started_at:
            duration = round((run.completed_at - run.started_at).total_seconds(), 1)
        run_history.append({
            "id":                   str(run.id),
            "started_at":           str(run.started_at),
            "completed_at":         str(run.completed_at) if run.completed_at else None,
            "status":               run.status,
            "queries_generated":    run.queries_generated or 0,
            "pages_fetched":        run.pages_fetched or 0,
            "opportunities_found":  run.opportunities_found or 0,
            "opportunities_updated": run.opportunities_updated or 0,
            "llm_calls":            run.llm_calls or 0,
            "llm_cost_usd":         cost,
            "search_calls":         run.search_calls or 0,
            "errors_count":         len(run.errors or []),
            "errors":               (run.errors or [])[:3],
            "duration_seconds":     duration,
        })

    # Wave 2: user-scoped stats (only if user found)
    opp_stats: dict = {"total": 0, "free_tuition_count": 0, "with_deadline_count": 0, "by_eligibility": {}, "by_score_band": {}}
    notif_summary: dict = {"total_sent": 0, "by_type": {}}

    if user_id:
        opp_stats, notif_summary = await asyncio.gather(
            _opp_stats(db, user_id),
            _notif_stats(db, user_id),
        )

    avg_cost = total_cost / len(runs) if runs else 0
    cost_summary = {
        "total_llm_cost_usd":        round(total_cost, 6),
        "avg_cost_per_run_usd":      round(avg_cost, 6),
        "total_pages_fetched":       total_pages,
        "total_opportunities_found": total_found,
        "runs_completed":   sum(1 for r in runs if r.status == "completed"),
        "runs_with_errors": sum(1 for r in runs if r.status in ("partial", "failed")),
    }

    return {
        "generated_at":      str(datetime.utcnow()),
        "health":            health,
        "last_research_run": run_history[0] if run_history else None,
        "opportunities":     opp_stats,
        "costs":             cost_summary,
        "notifications":     notif_summary,
        "recent_runs":       run_history,
    }


# ─── /runs ────────────────────────────────────────────────────────────────

@router.get("/runs")
async def get_research_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Research run history with full details."""
    runs = await _get_runs(db, limit)
    return [
        {
            "id":                   str(r.id),
            "started_at":           str(r.started_at),
            "completed_at":         str(r.completed_at) if r.completed_at else None,
            "status":               r.status,
            "queries_generated":    r.queries_generated,
            "pages_fetched":        r.pages_fetched,
            "opportunities_found":  r.opportunities_found,
            "opportunities_updated": r.opportunities_updated,
            "llm_calls":            r.llm_calls,
            "llm_cost_usd":         float(r.llm_cost_usd or 0),
            "search_calls":         r.search_calls,
            "errors":               r.errors or [],
            "notes":                r.notes,
        }
        for r in runs
    ]


# ─── /stats ───────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_quick_stats(db: AsyncSession = Depends(get_db)):
    """Lightweight stats — all queries run concurrently."""
    user_id = await _get_user_id(db, _USER_EMAIL)
    if not user_id:
        return {"error": "User not found"}

    today  = date.today()
    cutoff = today + timedelta(days=30)

    total_r, eligible_r, upcoming_r, last_run_r = await asyncio.gather(
        db.execute(
            select(func.count(Opportunity.id))
            .where(Opportunity.user_id == user_id)
        ),
        db.execute(
            select(func.count(Opportunity.id))
            .where(Opportunity.user_id == user_id)
            .where(Opportunity.eligibility_status.in_(["eligible", "probably_eligible"]))
        ),
        db.execute(
            select(func.count(Opportunity.id))
            .where(Opportunity.user_id == user_id)
            .where(Opportunity.application_deadline >= today)
            .where(Opportunity.application_deadline <= cutoff)
        ),
        db.execute(
            select(ResearchRun.started_at, ResearchRun.status)
            .order_by(desc(ResearchRun.started_at))
            .limit(1)
        ),
    )

    run_row = last_run_r.first()
    return {
        "total_opportunities":    total_r.scalar() or 0,
        "eligible_opportunities": eligible_r.scalar() or 0,
        "deadlines_in_30_days":   upcoming_r.scalar() or 0,
        "last_research_run":      str(run_row[0]) if run_row else None,
        "last_run_status":        run_row[1] if run_row else None,
        "scheduler_running":      scheduler.running,
    }
