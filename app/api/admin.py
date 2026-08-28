"""
app/api/admin.py
─────────────────
Admin / observability endpoints.

These endpoints give you visibility into what the system is doing:
- Is the database connected?
- Are scheduled jobs running?
- How many opportunities have been discovered?
- How much have LLM calls cost?
- What errors occurred in the last research run?
- When did the last research run complete?

WHY OBSERVABILITY MATTERS:
Without it, you're flying blind. The agent runs at 08:00 while you sleep.
Did it find anything? Did it crash? How much did it cost?
These endpoints answer those questions without needing to SSH into a server
or query the database manually.

A professional engineer would call this "operational visibility".
It's the difference between a system you trust and one you fear.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
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

_USER_EMAIL = "mahmudunmiraz@gmail.com"


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Full system dashboard — everything you need to know at a glance.
    """
    settings = get_settings()

    # ── System health ────────────────────────────────────────────────────
    db_ok = False
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    health = {
        "database": "connected" if db_ok else "error",
        "llm_configured": bool(settings.gemini_api_key),
        "search_configured": bool(settings.tavily_api_key),
        "telegram_enabled": settings.telegram_enabled,
        "scheduler_running": scheduler.running,
        "scheduler_jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            }
            for job in scheduler.get_jobs()
        ],
    }

    # ── Research run history (last 10) ───────────────────────────────────
    runs_result = await db.execute(
        select(ResearchRun)
        .order_by(desc(ResearchRun.started_at))
        .limit(10)
    )
    runs = runs_result.scalars().all()

    run_history = []
    total_llm_cost = 0.0
    total_pages_fetched = 0
    total_opportunities_found = 0

    for run in runs:
        cost = float(run.llm_cost_usd or 0)
        total_llm_cost += cost
        total_pages_fetched += run.pages_fetched or 0
        total_opportunities_found += run.opportunities_found or 0

        duration = None
        if run.completed_at and run.started_at:
            duration = round((run.completed_at - run.started_at).total_seconds(), 1)

        run_history.append({
            "id": str(run.id),
            "started_at": str(run.started_at),
            "completed_at": str(run.completed_at) if run.completed_at else None,
            "status": run.status,
            "queries_generated": run.queries_generated or 0,
            "pages_fetched": run.pages_fetched or 0,
            "opportunities_found": run.opportunities_found or 0,
            "opportunities_updated": run.opportunities_updated or 0,
            "llm_calls": run.llm_calls or 0,
            "llm_cost_usd": cost,
            "search_calls": run.search_calls or 0,
            "errors_count": len(run.errors or []),
            "errors": (run.errors or [])[:3],  # show first 3 errors only
            "duration_seconds": duration,
        })

    # ── Opportunity statistics ───────────────────────────────────────────
    user_result = await db.execute(select(User).where(User.email == _USER_EMAIL))
    user = user_result.scalar_one_or_none()

    opp_stats = {
        "total": 0,
        "by_eligibility": {},
        "by_score_band": {
            "exceptional_90_plus": 0,
            "strong_75_89": 0,
            "good_60_74": 0,
            "moderate_45_59": 0,
            "weak_below_45": 0,
        },
        "free_tuition_count": 0,
        "with_deadline_count": 0,
        "top_countries": [],
    }

    if user:
        opps_result = await db.execute(
            select(Opportunity)
            .where(Opportunity.user_id == user.id)
        )
        opps = opps_result.scalars().all()
        opp_stats["total"] = len(opps)

        eligibility_counts: dict[str, int] = {}
        for opp in opps:
            # By eligibility
            e = opp.eligibility_status
            eligibility_counts[e] = eligibility_counts.get(e, 0) + 1

            # By score band
            score = float(opp.total_score or 0)
            if score >= 90:
                opp_stats["by_score_band"]["exceptional_90_plus"] += 1
            elif score >= 75:
                opp_stats["by_score_band"]["strong_75_89"] += 1
            elif score >= 60:
                opp_stats["by_score_band"]["good_60_74"] += 1
            elif score >= 45:
                opp_stats["by_score_band"]["moderate_45_59"] += 1
            else:
                opp_stats["by_score_band"]["weak_below_45"] += 1

            # Deadline presence
            if opp.application_deadline:
                opp_stats["with_deadline_count"] += 1

        opp_stats["by_eligibility"] = eligibility_counts

        # Free tuition count (via join)
        free_result = await db.execute(
            select(func.count(Opportunity.id))
            .join(Programme, Programme.id == Opportunity.programme_id)
            .where(Opportunity.user_id == user.id)
            .where(Programme.tuition_eur_per_year == 0)
        )
        opp_stats["free_tuition_count"] = free_result.scalar() or 0

    # ── Cost summary ─────────────────────────────────────────────────────
    avg_cost = total_llm_cost / len(runs) if runs else 0
    cost_summary = {
        "total_llm_cost_usd": round(total_llm_cost, 6),
        "avg_cost_per_run_usd": round(avg_cost, 6),
        "total_pages_fetched": total_pages_fetched,
        "total_opportunities_found": total_opportunities_found,
        "runs_completed": len([r for r in runs if r.status == "completed"]),
        "runs_with_errors": len([r for r in runs if r.status in ("partial", "failed")]),
    }

    # ── Notification summary ─────────────────────────────────────────────
    notif_summary = {"total_sent": 0, "by_type": {}}
    if user:
        notifs_result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user.id)
            .where(Notification.sent_at.isnot(None))
        )
        notifs = notifs_result.scalars().all()
        notif_summary["total_sent"] = len(notifs)
        for n in notifs:
            notif_summary["by_type"][n.notification_type] = (
                notif_summary["by_type"].get(n.notification_type, 0) + 1
            )

    # ── Last research run summary ─────────────────────────────────────────
    last_run = run_history[0] if run_history else None

    return {
        "generated_at": str(datetime.utcnow()),
        "health": health,
        "last_research_run": last_run,
        "opportunities": opp_stats,
        "costs": cost_summary,
        "notifications": notif_summary,
        "recent_runs": run_history,
    }


@router.get("/runs")
async def get_research_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get research run history with full details."""
    result = await db.execute(
        select(ResearchRun)
        .order_by(desc(ResearchRun.started_at))
        .limit(limit)
    )
    runs = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "started_at": str(r.started_at),
            "completed_at": str(r.completed_at) if r.completed_at else None,
            "status": r.status,
            "queries_generated": r.queries_generated,
            "pages_fetched": r.pages_fetched,
            "opportunities_found": r.opportunities_found,
            "opportunities_updated": r.opportunities_updated,
            "llm_calls": r.llm_calls,
            "llm_cost_usd": float(r.llm_cost_usd or 0),
            "search_calls": r.search_calls,
            "errors": r.errors or [],
            "notes": r.notes,
        }
        for r in runs
    ]


@router.get("/stats")
async def get_quick_stats(db: AsyncSession = Depends(get_db)):
    """Quick stats for a status bar or header widget."""
    user_result = await db.execute(select(User).where(User.email == _USER_EMAIL))
    user = user_result.scalar_one_or_none()

    if not user:
        return {"error": "User not found"}

    total_opps = await db.execute(
        select(func.count(Opportunity.id)).where(Opportunity.user_id == user.id)
    )
    eligible_opps = await db.execute(
        select(func.count(Opportunity.id))
        .where(Opportunity.user_id == user.id)
        .where(Opportunity.eligibility_status.in_(["eligible", "probably_eligible"]))
    )
    last_run = await db.execute(
        select(ResearchRun).order_by(desc(ResearchRun.started_at)).limit(1)
    )
    run = last_run.scalar_one_or_none()

    from datetime import date, timedelta
    upcoming = await db.execute(
        select(func.count(Opportunity.id))
        .where(Opportunity.user_id == user.id)
        .where(Opportunity.application_deadline >= date.today())
        .where(Opportunity.application_deadline <= date.today() + timedelta(days=30))
    )

    return {
        "total_opportunities": total_opps.scalar() or 0,
        "eligible_opportunities": eligible_opps.scalar() or 0,
        "deadlines_in_30_days": upcoming.scalar() or 0,
        "last_research_run": str(run.started_at) if run else None,
        "last_run_status": run.status if run else None,
        "scheduler_running": scheduler.running,
    }
