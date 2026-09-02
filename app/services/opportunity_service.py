"""
app/services/opportunity_service.py
─────────────────────────────────────
Persists discovered opportunities to the database.
Handles deduplication, change detection, and upsert logic.

KEY CONCEPTS:

UPSERT (Update or Insert):
  If a programme already exists, update it.
  If it doesn't exist, create it.
  Never create duplicates.

DEDUPLICATION STRATEGY:
  We identify duplicates by matching on:
    - University name (normalized: lowercase, stripped)
    - Programme name (normalized)
  This is imperfect (different spellings exist) but good enough for V1.

CHANGE DETECTION:
  When we re-fetch a known programme, we compare key fields.
  If the deadline, tuition, or requirements changed → flag as notable change.
  This triggers a notification to the user.

WHY NOT JUST DELETE AND RE-INSERT?
  Because you may have notes, application status, and other data attached
  to an opportunity. Deleting it would lose that data.
  Upsert preserves your application tracking history.
"""

import uuid
from datetime import datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.extraction_agent import ExtractedProgramme
from app.models.opportunity import Opportunity
from app.models.programme import Programme, ProgrammeRequirement, University
from app.models.research import ResearchRun
from app.models.source import Source
from app.services.eligibility_service import EligibilityResult, EligibilityStatus
from app.services.scoring_service import ScoreResult
from app.utils.date_parser import parse_date_safe

logger = structlog.get_logger(__name__)


def _normalize(text: str | None) -> str:
    """Normalize text for deduplication matching."""
    if not text:
        return ""
    return text.lower().strip().replace("  ", " ")


async def save_source(
    db: AsyncSession,
    url: str,
    source_type: str = "edu_database",
    tier: int = 4,
    title: str | None = None,
    content_hash: str | None = None,
) -> Source:
    """Save or update a source record. Returns the source."""
    # Check if source already exists by URL
    result = await db.execute(select(Source).where(Source.url == url))
    source = result.scalar_one_or_none()

    if source:
        # Update last verified time and hash
        source.last_verified_at = datetime.utcnow()
        if content_hash:
            old_hash = source.raw_content_hash
            source.raw_content_hash = content_hash
            if old_hash and old_hash != content_hash:
                logger.info("source_content_changed", url=url[:80])
    else:
        source = Source(
            url=url,
            source_type=source_type,
            tier=tier,
            title=title,
            raw_content_hash=content_hash,
        )
        db.add(source)

    return source


async def upsert_university(
    db: AsyncSession,
    name: str,
    country: str | None = None,
    city: str | None = None,
) -> University:
    """Find or create a university record. Updates country/city if previously unknown."""
    name_normalized = _normalize(name)

    result = await db.execute(
        select(University).where(University.name.ilike(f"%{name_normalized}%"))
    )
    university = result.scalar_one_or_none()

    if not university:
        university = University(
            name=name,
            country=country or "Unknown",
            city=city,
        )
        db.add(university)
        logger.info("university_created", name=name, country=country)
    else:
        # Update country/city if we now have better info
        if country and (not university.country or university.country == "Unknown"):
            university.country = country
        if city and not university.city:
            university.city = city

    return university


async def upsert_programme(
    db: AsyncSession,
    extracted: ExtractedProgramme,
    university: University,
    source: Source,
) -> tuple[Programme, bool]:
    """
    Find or create a programme record.

    Returns:
        (programme, is_new) — is_new=True if this is a newly discovered programme
    """
    name_normalized = _normalize(extracted.programme_name or "")
    uni_id = university.id

    # Try to find existing programme at this university with this name
    result = await db.execute(
        select(Programme).where(
            Programme.university_id == uni_id,
            Programme.name.ilike(f"%{name_normalized}%"),
        )
    )
    existing = result.scalar_one_or_none()
    is_new = existing is None

    if existing:
        programme = existing
        # Update fields that might have changed
        if extracted.tuition_eur_per_year is not None:
            programme.tuition_eur_per_year = extracted.tuition_eur_per_year
        if extracted.tuition_notes:
            programme.tuition_notes = extracted.tuition_notes
        if extracted.official_url:
            programme.official_url = extracted.official_url
        if extracted.application_portal_url:
            programme.application_portal_url = extracted.application_portal_url
        if extracted.intake_months:
            programme.intake_months = extracted.intake_months
        programme.status = "active"
        logger.info("programme_updated", name=programme.name)
    else:
        programme = Programme(
            university_id=university.id,
            name=extracted.programme_name or "Unknown Programme",
            degree_type=extracted.degree_type or "MSc",
            field=extracted.field or "Computer Science",
            language=extracted.language_of_instruction or "English",
            duration_months=extracted.duration_months,
            tuition_eur_per_year=extracted.tuition_eur_per_year,
            tuition_notes=extracted.tuition_notes,
            intake_months=extracted.intake_months or [],
            official_url=extracted.official_url,
            application_portal_url=extracted.application_portal_url,
            status="unverified",
        )
        db.add(programme)
        logger.info("programme_created", name=programme.name, university=university.name)

    # Flush to get programme.id for requirements
    await db.flush()

    # Save requirements (replace all — simpler than diffing)
    if extracted.requirements and is_new:
        for req in extracted.requirements:
            requirement = ProgrammeRequirement(
                programme_id=programme.id,
                source_id=source.id,
                requirement_type=req.requirement_type,
                value=req.value,
                is_strict=req.is_strict,
                confidence=float(req.confidence) if req.confidence else None,
                raw_text=req.raw_text,
            )
            db.add(requirement)

    return programme, is_new


async def upsert_opportunity(
    db: AsyncSession,
    user_id: uuid.UUID,
    programme: Programme,
    eligibility: EligibilityResult,
    score: ScoreResult,
    extracted: ExtractedProgramme,
    source: Source,
) -> tuple[Opportunity, bool]:
    """
    Find or create an opportunity record.

    Returns:
        (opportunity, is_new)
    """
    # Find existing opportunity for this user + programme
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.user_id == user_id,
            Opportunity.programme_id == programme.id,
            Opportunity.scholarship_id.is_(None),
        )
    )
    existing = result.scalar_one_or_none()
    is_new = existing is None

    # Parse deadline
    deadline = None
    if extracted.application_deadline:
        deadline = parse_date_safe(extracted.application_deadline)

    # Detect notable changes
    is_notable_change = False
    if existing:
        old_score = float(existing.total_score or 0)
        new_score = score.total_score
        old_deadline = existing.application_deadline
        if abs(old_score - new_score) >= 5:
            is_notable_change = True
        if old_deadline != deadline and deadline is not None:
            is_notable_change = True

    if existing:
        opportunity = existing
        opportunity.eligibility_status = eligibility.status.value
        opportunity.eligibility_notes = eligibility.summary
        opportunity.total_score = score.total_score
        opportunity.score_breakdown = score.breakdown_dict
        opportunity.score_explanation = score.explanation
        opportunity.application_deadline = deadline
        opportunity.deadline_source_id = source.id
        opportunity.is_notable_change = is_notable_change
        opportunity.last_updated_at = datetime.utcnow()
        logger.info(
            "opportunity_updated",
            programme=programme.name,
            score=score.total_score,
            notable_change=is_notable_change,
        )
    else:
        opportunity = Opportunity(
            user_id=user_id,
            programme_id=programme.id,
            scholarship_id=None,
            eligibility_status=eligibility.status.value,
            eligibility_notes=eligibility.summary,
            total_score=score.total_score,
            score_breakdown=score.breakdown_dict,
            score_explanation=score.explanation,
            application_deadline=deadline,
            deadline_source_id=source.id,
            is_notable_change=False,
        )
        db.add(opportunity)
        logger.info(
            "opportunity_created",
            programme=programme.name,
            score=score.total_score,
            eligibility=eligibility.status.value,
        )

    return opportunity, is_new
