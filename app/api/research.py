"""
app/api/research.py
────────────────────
REST API endpoints for triggering and monitoring research cycles.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.services.research_orchestrator import run_research_cycle

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRunRequest(BaseModel):
    user_email: str
    max_queries: int = 10       # increased from 5
    max_urls_per_query: int = 4  # increased from 3
    dry_run: bool = False


class ResearchRunResponse(BaseModel):
    status: str
    queries_generated: int
    pages_fetched: int
    opportunities_found: int
    opportunities_updated: int
    errors_count: int
    message: str


@router.post("/run", response_model=ResearchRunResponse)
async def trigger_research_run(
    request: ResearchRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a research cycle synchronously.
    Returns when the cycle completes.
    For production use, this should run as a background task.
    """
    settings = get_settings()

    # Validate email matches configured user (security check)
    # In a single-user system, we just verify the user exists
    try:
        run = await run_research_cycle(
            db=db,
            user_email=request.user_email,
            max_queries=request.max_queries,
            max_urls_per_query=request.max_urls_per_query,
            dry_run=request.dry_run,
        )
        return ResearchRunResponse(
            status=run.status,
            queries_generated=run.queries_generated or 0,
            pages_fetched=run.pages_fetched or 0,
            opportunities_found=run.opportunities_found or 0,
            opportunities_updated=run.opportunities_updated or 0,
            errors_count=len(run.errors) if run.errors else 0,
            message=f"Research cycle {'completed' if run.status == 'completed' else 'completed with errors'}",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research cycle failed: {e}")
