"""
app/api/opportunities.py
─────────────────────────
REST API for querying and browsing discovered opportunities.

Endpoints:
  GET  /opportunities              List all opportunities (filterable, sortable)
  GET  /opportunities/{id}         Get a single opportunity with full details
  GET  /opportunities/top          Top opportunities by score
  GET  /opportunities/deadlines    Upcoming deadlines
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.application import Application
from app.models.opportunity import Opportunity
from app.models.programme import Programme, ProgrammeRequirement, University
from app.schemas.opportunity import OpportunityListOut, OpportunityOut, ProgrammeOut, UniversityOut, RequirementOut
from app.utils.date_parser import is_upcoming

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _build_opportunity_out(opp: Opportunity, app_status: str | None = None) -> OpportunityOut:
    """Build an OpportunityOut from an Opportunity ORM object."""
    programme_out = None
    university_out = None

    if opp.programme:
        prog = opp.programme
        requirements = [
            RequirementOut(
                requirement_type=r.requirement_type,
                value=r.value,
                is_strict=r.is_strict,
                confidence=float(r.confidence) if r.confidence else None,
                raw_text=r.raw_text,
            )
            for r in (prog.requirements or [])
        ]
        programme_out = ProgrammeOut(
            id=prog.id,
            name=prog.name,
            degree_type=prog.degree_type,
            field=prog.field,
            language=prog.language,
            duration_months=prog.duration_months,
            tuition_eur_per_year=prog.tuition_eur_per_year,
            tuition_notes=prog.tuition_notes,
            is_tuition_free=(prog.tuition_eur_per_year == 0),
            intake_months=list(prog.intake_months or []),
            official_url=prog.official_url,
            application_portal_url=prog.application_portal_url,
            status=prog.status,
            requirements=requirements,
        )
        if prog.university:
            uni = prog.university
            university_out = UniversityOut(
                id=uni.id,
                name=uni.name,
                country=uni.country,
                city=uni.city,
                official_url=uni.official_url,
                qs_rank=uni.qs_rank,
            )

    return OpportunityOut(
        id=opp.id,
        eligibility_status=opp.eligibility_status,
        eligibility_notes=opp.eligibility_notes,
        total_score=float(opp.total_score) if opp.total_score else None,
        score_breakdown=opp.score_breakdown,
        score_explanation=opp.score_explanation,
        score_label=None,  # computed_field will fill this
        application_deadline=opp.application_deadline,
        scholarship_deadline=opp.scholarship_deadline,
        first_discovered_at=opp.first_discovered_at,
        last_updated_at=opp.last_updated_at,
        is_notable_change=opp.is_notable_change,
        programme=programme_out,
        university=university_out,
        application_status=app_status,
    )


@router.get("", response_model=OpportunityListOut)
async def list_opportunities(
    eligibility: str | None = Query(None, description="Filter by eligibility status"),
    min_score: float | None = Query(None, description="Minimum score (0-100)"),
    max_tuition: int | None = Query(None, description="Maximum tuition EUR/year"),
    country: str | None = Query(None, description="Filter by country name"),
    sort_by: str = Query("score", description="Sort by: score, deadline, discovered"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List all discovered opportunities with optional filtering and sorting.

    This is the main endpoint for browsing your opportunities.
    """
    # Build base query with eager loading of related data
    query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.programme).options(
                selectinload(Programme.university),
                selectinload(Programme.requirements),
            )
        )
    )

    # Apply filters
    if eligibility:
        query = query.where(Opportunity.eligibility_status == eligibility)
    if min_score is not None:
        query = query.where(Opportunity.total_score >= min_score)

    # Apply sorting
    if sort_by == "score":
        query = query.order_by(desc(Opportunity.total_score))
    elif sort_by == "deadline":
        query = query.order_by(Opportunity.application_deadline)
    elif sort_by == "discovered":
        query = query.order_by(desc(Opportunity.first_discovered_at))

    # Count total
    count_result = await db.execute(query)
    all_items = count_result.scalars().all()
    total = len(all_items)

    # Apply pagination
    offset = (page - 1) * page_size
    paginated = all_items[offset: offset + page_size]

    # Load application statuses for these opportunities
    if paginated:
        opp_ids = [o.id for o in paginated]
        app_result = await db.execute(
            select(Application).where(Application.opportunity_id.in_(opp_ids))
        )
        apps_by_opp = {a.opportunity_id: a.status for a in app_result.scalars().all()}
    else:
        apps_by_opp = {}

    # Filter by country (post-load, since country is on university)
    items = []
    for opp in paginated:
        if country and opp.programme and opp.programme.university:
            if country.lower() not in opp.programme.university.country.lower():
                continue
        app_status = apps_by_opp.get(opp.id)
        items.append(_build_opportunity_out(opp, app_status))

    return OpportunityListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.get("/top", response_model=list[OpportunityOut])
async def get_top_opportunities(
    limit: int = Query(10, ge=1, le=50),
    min_score: float = Query(60.0),
    db: AsyncSession = Depends(get_db),
):
    """Get the top N opportunities by score."""
    query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.programme).options(
                selectinload(Programme.university),
                selectinload(Programme.requirements),
            )
        )
        .where(Opportunity.total_score >= min_score)
        .where(Opportunity.eligibility_status != "ineligible")
        .order_by(desc(Opportunity.total_score))
        .limit(limit)
    )
    result = await db.execute(query)
    opps = result.scalars().all()
    return [_build_opportunity_out(o) for o in opps]


@router.get("/deadlines", response_model=list[OpportunityOut])
async def get_upcoming_deadlines(
    within_days: int = Query(30, description="Show deadlines within this many days"),
    db: AsyncSession = Depends(get_db),
):
    """Get opportunities with deadlines approaching within N days."""
    from datetime import date, timedelta
    today = date.today()
    cutoff = today + timedelta(days=within_days)

    query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.programme).options(
                selectinload(Programme.university),
            )
        )
        .where(Opportunity.application_deadline >= today)
        .where(Opportunity.application_deadline <= cutoff)
        .where(Opportunity.eligibility_status != "ineligible")
        .order_by(Opportunity.application_deadline)
    )
    result = await db.execute(query)
    opps = result.scalars().all()
    return [_build_opportunity_out(o) for o in opps]


@router.get("/{opportunity_id}", response_model=OpportunityOut)
async def get_opportunity(
    opportunity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single opportunity with full details."""
    query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.programme).options(
                selectinload(Programme.university),
                selectinload(Programme.requirements),
            )
        )
        .where(Opportunity.id == opportunity_id)
    )
    result = await db.execute(query)
    opp = result.scalar_one_or_none()

    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Get application status
    app_result = await db.execute(
        select(Application).where(Application.opportunity_id == opportunity_id)
    )
    app = app_result.scalar_one_or_none()

    return _build_opportunity_out(opp, app.status if app else None)
