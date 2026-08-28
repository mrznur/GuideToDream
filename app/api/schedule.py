"""
app/api/schedule.py
────────────────────
API endpoints for scheduler status and manual job triggering.

WHY MANUAL TRIGGERS?
The scheduler runs jobs automatically, but sometimes you want to:
- Run a research cycle right now without waiting for 08:00
- Test the deadline checker
- Verify the daily summary looks correct

These endpoints let you trigger any job on demand.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.scheduler.jobs import deadline_job, research_job, scheduler, summary_job

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/status")
async def get_scheduler_status():
    """Get the current scheduler status and next run times for all jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else "not scheduled",
            "trigger": str(job.trigger),
        })

    return {
        "running": scheduler.running,
        "jobs": jobs,
        "total_jobs": len(jobs),
    }


@router.post("/trigger/research")
async def trigger_research_now(background_tasks: BackgroundTasks):
    """
    Manually trigger a research cycle right now.
    Runs in the background so the HTTP response returns immediately.
    """
    background_tasks.add_task(research_job)
    return {
        "status": "triggered",
        "message": "Research cycle started in background. Check /api/v1/research/run history for results.",
    }


@router.post("/trigger/deadlines")
async def trigger_deadline_check(background_tasks: BackgroundTasks):
    """Manually trigger a deadline check and send reminders."""
    background_tasks.add_task(deadline_job)
    return {"status": "triggered", "message": "Deadline check started in background."}


@router.post("/trigger/summary")
async def trigger_daily_summary(background_tasks: BackgroundTasks):
    """Manually trigger the daily summary notification."""
    background_tasks.add_task(summary_job)
    return {"status": "triggered", "message": "Daily summary started in background."}
