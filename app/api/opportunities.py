"""
app/api/opportunities.py
─────────────────────────
REST API for querying and browsing discovered opportunities.

Endpoints:
  GET  /opportunities              List (filterable, sortable, paginated)
  GET  /opportunities/top          Top N by score
  GET  /opportunities/deadlines    Upcoming deadlines
  GET  /opportunities/{id}         Single opportunity with full detail

PERFORMANCE: All pagination is done at the DB level (LIMIT/OFFSET + COUNT
query) — we never load all rows into Python just to count or slice them.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.application import Application
from app.models.opportunity import Opportunity
from app.models.programme import Programme, ProgrammeRequirement, University
from app.schemas.opportunity import (
    OpportunityListOut,
    OpportunityOut,
    ProgrammeOut,
    RequirementOut,
    UniversityOut,
)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


# ─── Builder ──────────────────────────────────────────────────────────────

def _build_opportunity_out(
    opp: Opportunity, app_status: str | None = None
) -> OpportunityOut:
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
        score_label=None,  # computed_field fills this
        application_deadline=opp.application_deadline,
        scholarship_deadline=opp.scholarship_deadline,
        first_discovered_at=opp.first_discovered_at,
        last_updated_at=opp.last_updated_at,
        is_notable_change=opp.is_notable_change,
        programme=programme_out,
        university=university_out,
        application_status=app_status,
    )


def _apply_filters(query: Select, eligibility: str | None, min_score: float | None) -> Select:
    """Apply WHERE clauses common to list and count queries."""
    if eligibility:
        query = query.where(Opportunity.eligibility_status == eligibility)
    if min_score is not None:
        query = query.where(Opportunity.total_score >= min_score)
    return query


def _apply_sort(query: Select, sort_by: str) -> Select:
    if sort_by == "deadline":
        return query.order_by(Opportunity.application_deadline.asc().nulls_last())
    if sort_by == "discovered":
        return query.order_by(desc(Opportunity.first_discovered_at))
    return query.order_by(desc(Opportunity.total_score))  # default: score


# ─── Endpoints ────────────────────────────────────────────────────────────

@router.get("", response_model=OpportunityListOut)
async def list_opportunities(
    eligibility: str | None = Query(None),
    min_score: float | None = Query(None),
    max_tuition: int | None = Query(None),
    country: str | None = Query(None),
    sort_by: str = Query("score"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List opportunities with filtering, sorting, and DB-level pagination.

    Pagination is done entirely in PostgreSQL (LIMIT/OFFSET + COUNT(*)).
    We never load all rows into Python.
    """
    import asyncio

    # ── Build base filter (reused for count + data queries) ──────────────
    base = _apply_filters(select(Opportunity), eligibility, min_score)

    # Country filter needs a join — add it if requested
    if country or max_tuition is not None:
        base = base.join(Programme, Programme.id == Opportunity.programme_id)
        if country:
            base = base.join(University, University.id == Programme.university_id).where(
                University.country.ilike(f"%{country}%")
            )
        if max_tuition is not None:
            base = base.where(
                (Programme.tuition_eur_per_year <= max_tuition)
                | (Programme.tuition_eur_per_year.is_(None))
            )

    # ── COUNT query (no ordering, no loading) ────────────────────────────
    count_q = select(func.count()).select_from(base.subquery())

    # ── Data query (ordered, paginated, eager-loaded) ────────────────────
    data_q = (
        _apply_sort(base, sort_by)
        .options(
            selectinload(Opportunity.programme).options(
                selectinload(Programme.university),
                selectinload(Programme.requirements),
            )
        )
        .limit(page_size)
        .offset((page - 1) * page_size)
    )

    # Run sequentially — asyncio.gather on a single AsyncSession is unsafe
    # (asyncpg connections do not support concurrent queries on one session)
    count_result = await db.execute(count_q)
    data_result  = await db.execute(data_q)

    total = count_result.scalar() or 0
    opps  = data_result.scalars().all()

    # Load application statuses for this page only
    if opps:
        opp_ids = [o.id for o in opps]
        app_result = await db.execute(
            select(Application.opportunity_id, Application.status)
            .where(Application.opportunity_id.in_(opp_ids))
        )
        apps_by_opp: dict = {row.opportunity_id: row.status for row in app_result.all()}
    else:
        apps_by_opp = {}

    items = [_build_opportunity_out(opp, apps_by_opp.get(opp.id)) for opp in opps]

    return OpportunityListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=((page - 1) * page_size + len(items)) < total,
    )


@router.get("/top", response_model=list[OpportunityOut])
async def get_top_opportunities(
    limit: int = Query(10, ge=1, le=50),
    min_score: float = Query(60.0),
    db: AsyncSession = Depends(get_db),
):
    """Top N opportunities by score, excluding ineligible."""
    result = await db.execute(
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
    return [_build_opportunity_out(o) for o in result.scalars().all()]


@router.get("/deadlines", response_model=list[OpportunityOut])
async def get_upcoming_deadlines(
    within_days: int = Query(30),
    db: AsyncSession = Depends(get_db),
):
    """Opportunities with deadlines approaching within N days."""
    from datetime import date, timedelta
    today  = date.today()
    cutoff = today + timedelta(days=within_days)

    result = await db.execute(
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
    return [_build_opportunity_out(o) for o in result.scalars().all()]


@router.get("/{opportunity_id}", response_model=OpportunityOut)
async def get_opportunity(
    opportunity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Single opportunity with full details + application status."""
    import asyncio

    opp_q   = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.programme).options(
                selectinload(Programme.university),
                selectinload(Programme.requirements),
            )
        )
        .where(Opportunity.id == opportunity_id)
    )
    app_q   = select(Application).where(Application.opportunity_id == opportunity_id)

    opp_res = await db.execute(opp_q)
    opp = opp_res.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    app_res = await db.execute(app_q)
    app = app_res.scalar_one_or_none()
    return _build_opportunity_out(opp, app.status if app else None)
