"""
app/api/applications.py
────────────────────────
REST API for the application pipeline tracker.

The application tracker maintains your pipeline:
  discovered → shortlisted → preparing → applied → interview → accepted/rejected/withdrawn

KEY DESIGN: State machine enforcement
Invalid transitions are rejected with a 422 error.
You cannot go from "discovered" to "accepted" — that's not how applying works.

Endpoints:
  GET    /applications                   List all applications
  GET    /applications/{id}              Get one application
  POST   /applications                   Create (usually auto-created)
  PATCH  /applications/{id}/status       Transition to new status
  PUT    /applications/{id}              Full update (notes, applied_at)
  GET    /applications/pipeline          Pipeline summary view
"""

from uuid import UUID

from app.config import get_settings
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.application import Application, APPLICATION_STATUSES
from app.models.opportunity import Opportunity
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate, StatusTransitionRequest

router = APIRouter(prefix="/applications", tags=["applications"])

# Hardcoded user email for single-user system
_USER_EMAIL: str = get_settings().user_email


async def _get_user_id(db: AsyncSession) -> UUID:
    """Get the single user's ID."""
    result = await db.execute(select(User).where(User.email == _USER_EMAIL))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found. Run the seed script.")
    return user.id


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all applications, optionally filtered by status."""
    user_id = await _get_user_id(db)
    query = select(Application).where(Application.user_id == user_id)
    if status:
        if status not in APPLICATION_STATUSES:
            raise HTTPException(status_code=422, detail=f"Invalid status. Choose from: {APPLICATION_STATUSES}")
        query = query.where(Application.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/pipeline")
async def get_pipeline_summary(db: AsyncSession = Depends(get_db)):
    """
    Returns a summary of your application pipeline.
    Shows counts per status stage.
    """
    user_id = await _get_user_id(db)
    result = await db.execute(
        select(Application).where(Application.user_id == user_id)
    )
    apps = result.scalars().all()

    pipeline = {status: [] for status in APPLICATION_STATUSES}
    for app in apps:
        if app.status in pipeline:
            pipeline[app.status].append(str(app.opportunity_id))

    summary = {
        status: {
            "count": len(ids),
            "opportunity_ids": ids,
        }
        for status, ids in pipeline.items()
    }
    return {
        "pipeline": summary,
        "total": len(apps),
        "active": len([a for a in apps if a.status not in ("accepted", "rejected", "withdrawn")]),
    }


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single application record."""
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.post("", response_model=ApplicationOut, status_code=201)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create an application record for an opportunity.
    Usually auto-created when an opportunity is discovered,
    but can be created manually to track opportunities found externally.
    """
    user_id = await _get_user_id(db)

    # Verify opportunity exists
    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == data.opportunity_id)
    )
    if not opp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Check for duplicate
    existing = await db.execute(
        select(Application).where(
            Application.user_id == user_id,
            Application.opportunity_id == data.opportunity_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Application already exists for this opportunity")

    app = Application(
        user_id=user_id,
        opportunity_id=data.opportunity_id,
        status=data.status,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


@router.patch("/{application_id}/status", response_model=ApplicationOut)
async def transition_status(
    application_id: UUID,
    request: StatusTransitionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Transition an application to a new status.

    Enforces valid state transitions:
      discovered → shortlisted → preparing → applied → interview → accepted/rejected
    Invalid transitions return a 422 error.

    WHY ENFORCE THIS?
    Because "accepted" → "preparing" makes no sense.
    A state machine prevents invalid data from entering your pipeline.
    """
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    current = app.status
    if not request.is_valid_transition(current):
        allowed = StatusTransitionRequest.TRANSITIONS.get(current, [])
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid transition: '{current}' → '{request.new_status}'. "
                f"From '{current}', you can go to: {allowed or ['(terminal state)']}"
            ),
        )

    app.status = request.new_status
    if request.notes:
        app.notes = (app.notes or "") + f"\n[{request.new_status}] {request.notes}"
    if request.new_status == "applied":
        from datetime import date
        app.applied_at = app.applied_at or date.today()

    await db.commit()
    await db.refresh(app)
    return app


@router.put("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: UUID,
    data: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update notes and applied_at for an application."""
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if data.status is not None:
        app.status = data.status
    if data.applied_at is not None:
        app.applied_at = data.applied_at
    if data.notes is not None:
        app.notes = data.notes

    await db.commit()
    await db.refresh(app)
    return app
