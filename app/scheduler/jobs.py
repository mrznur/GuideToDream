"""
app/scheduler/jobs.py
──────────────────────
Scheduled job definitions for GuideToDream.

Three jobs run on a daily schedule:
  08:00 → research_job: discover new programmes and scholarships
  14:00 → deadline_job: check for approaching deadlines and notify
  21:00 → summary_job: send daily summary to Telegram

WHY APSCHEDULER INSIDE FASTAPI?
The alternative is a separate worker process (like Celery).
For a personal agent running a few jobs per day, a separate worker
is unnecessary complexity. APScheduler runs inside the same FastAPI
process, sharing the same database connection pool and config.

When to graduate to Celery:
- If you need jobs to survive app restarts (APScheduler in-memory loses jobs)
- If jobs are long-running and block other requests
- If you need distributed workers

For now: APScheduler is correct.

ASYNC JOBS:
APScheduler 3.x has limited async support. We use the asyncio executor
and run async functions via asyncio.run() in a thread pool.
APScheduler 4.x (beta) has full native async — we'll upgrade when stable.
"""

import asyncio
import logging

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings

logger = structlog.get_logger(__name__)

# Module-level scheduler instance — created once, started in lifespan
scheduler = AsyncIOScheduler(
    job_defaults={
        "coalesce": True,       # if job missed multiple times, run only once
        "max_instances": 1,     # never run the same job concurrently
        "misfire_grace_time": 3600,  # if missed by up to 1hr, still run it
    }
)


async def research_job():
    """
    Full research cycle: generate queries → search → fetch → extract →
    evaluate → save → notify.

    Runs at 08:00 daily.
    """
    logger.info("scheduled_research_job_started")
    try:
        from app.database import AsyncSessionLocal
        from app.services.research_orchestrator import run_research_cycle

        settings = get_settings()
        async with AsyncSessionLocal() as db:
            run = await run_research_cycle(
                db=db,
                user_email=settings.user_email,
                max_queries=8,
                max_urls_per_query=3,
            )
        logger.info(
            "scheduled_research_job_completed",
            status=run.status,
            found=run.opportunities_found,
            updated=run.opportunities_updated,
            errors=len(run.errors or []),
        )
    except Exception as e:
        logger.error("scheduled_research_job_failed", error=str(e))
        # Send failure notification so you know it broke
        from app.services.notification_service import send_telegram_message
        send_telegram_message(
            f"⚠️ <b>Research job failed</b>\n\nError: {str(e)[:200]}\n\n"
            f"Check the research_runs table for details."
        )


async def deadline_job():
    """
    Check for approaching deadlines and send reminders.

    Runs at 14:00 daily. Only notifies if not already notified today
    (suppression window = 1 day per opportunity).
    """
    logger.info("scheduled_deadline_job_started")
    try:
        from datetime import date, timedelta

        from sqlalchemy import desc, select
        from sqlalchemy.orm import selectinload

        from app.database import AsyncSessionLocal
        from app.models.opportunity import Opportunity
        from app.models.programme import Programme
        from app.models.user import User
        from app.services.notification_service import evaluate_and_notify
        from app.utils.date_parser import days_until

        settings = get_settings()

        async with AsyncSessionLocal() as db:
            # Load user
            user_result = await db.execute(
                select(User).where(User.email == get_settings().user_email)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                logger.warning("deadline_job_no_user")
                return

            # Find opportunities with deadlines in the next reminder window
            today = date.today()
            cutoff = today + timedelta(days=settings.deadline_reminder_days)

            opps_result = await db.execute(
                select(Opportunity)
                .options(
                    selectinload(Opportunity.programme).options(
                        selectinload(Programme.university)
                    )
                )
                .where(Opportunity.user_id == user.id)
                .where(Opportunity.application_deadline >= today)
                .where(Opportunity.application_deadline <= cutoff)
                .where(Opportunity.eligibility_status != "ineligible")
                .order_by(Opportunity.application_deadline)
            )
            opps = opps_result.scalars().all()

            notified = 0
            for opp in opps:
                sent = await evaluate_and_notify(db, user.id, opp, is_new=False)
                if sent:
                    notified += 1

            await db.commit()

        logger.info("scheduled_deadline_job_completed", opportunities_checked=len(opps), notified=notified)

    except Exception as e:
        logger.error("scheduled_deadline_job_failed", error=str(e))


async def summary_job():
    """
    Send a daily summary of top opportunities and pipeline status.

    Runs at 21:00 daily. Always sends regardless of suppression
    (daily summaries are expected daily).
    """
    logger.info("scheduled_summary_job_started")
    try:
        from sqlalchemy import desc, select
        from sqlalchemy.orm import selectinload

        from app.database import AsyncSessionLocal
        from app.models.application import Application
        from app.models.opportunity import Opportunity
        from app.models.programme import Programme
        from app.models.user import User
        from app.services.notification_service import send_daily_summary

        async with AsyncSessionLocal() as db:
            user_result = await db.execute(
                select(User).where(User.email == get_settings().user_email)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return

            # Load top 10 non-ineligible opportunities
            opps_result = await db.execute(
                select(Opportunity)
                .options(
                    selectinload(Opportunity.programme).options(
                        selectinload(Programme.university)
                    )
                )
                .where(Opportunity.user_id == user.id)
                .where(Opportunity.eligibility_status != "ineligible")
                .order_by(desc(Opportunity.total_score))
                .limit(10)
            )
            top_opps = opps_result.scalars().all()

            # Load application counts
            apps_result = await db.execute(
                select(Application).where(Application.user_id == user.id)
            )
            apps = apps_result.scalars().all()
            active_apps = [a for a in apps if a.status not in ("accepted", "rejected", "withdrawn")]

            sent = await send_daily_summary(db, user.id, top_opps)
            await db.commit()

        logger.info("scheduled_summary_job_completed", sent=sent, active_apps=len(active_apps))

    except Exception as e:
        logger.error("scheduled_summary_job_failed", error=str(e))


def setup_scheduler() -> AsyncIOScheduler:
    """
    Configure and return the scheduler with all jobs registered.
    Called once during app startup.
    """
    settings = get_settings()

    if not settings.scheduler_enabled:
        logger.info("scheduler_disabled")
        return scheduler

    # Research job — 08:00 daily
    scheduler.add_job(
        research_job,
        trigger=CronTrigger(
            hour=settings.research_schedule_hour,
            minute=settings.research_schedule_minute,
        ),
        id="research_daily",
        name="Daily Research Cycle",
        replace_existing=True,
    )

    # Deadline check — 14:00 daily
    scheduler.add_job(
        deadline_job,
        trigger=CronTrigger(
            hour=settings.deadline_check_hour,
            minute=settings.deadline_check_minute,
        ),
        id="deadline_daily",
        name="Daily Deadline Check",
        replace_existing=True,
    )

    # Daily summary — 21:00 daily
    scheduler.add_job(
        summary_job,
        trigger=CronTrigger(
            hour=settings.daily_summary_hour,
            minute=settings.daily_summary_minute,
        ),
        id="summary_daily",
        name="Daily Summary",
        replace_existing=True,
    )

    logger.info(
        "scheduler_configured",
        jobs=3,
        research_at=f"{settings.research_schedule_hour:02d}:{settings.research_schedule_minute:02d}",
        deadline_at=f"{settings.deadline_check_hour:02d}:{settings.deadline_check_minute:02d}",
        summary_at=f"{settings.daily_summary_hour:02d}:{settings.daily_summary_minute:02d}",
    )

    return scheduler
