"""
app/agents/assistant_agent.py
──────────────────────────────
Conversational assistant that answers questions about your opportunities.

PERFORMANCE NOTES:
- Uses call_llm_async so the FastAPI event loop is never blocked
- DB queries run concurrently (asyncio.gather)
- Context capped at top 20 opportunities to keep prompt small and fast
- Shared genai.Client reused across calls (no per-request connection overhead)
"""

import asyncio

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.opportunity import Opportunity
from app.models.programme import Programme
from app.utils.llm import LLMError, call_llm_async

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are a personal higher-education advisor.
Help a student track and evaluate European Master's programmes.

Answer based ONLY on the data below. Be specific and concise.
Plain text only — no markdown bold or headers.

PROFILE: {profile_summary}

TOP OPPORTUNITIES (up to 20):
{opportunities_data}

PIPELINE: {pipeline_data}

Question: {question}
Answer:"""


async def _load_profile(db: AsyncSession, user_email: str) -> str:
    from app.models.user import User
    from app.models.profile import Profile, ProfilePreferences

    user_row = await db.execute(select(User).where(User.email == user_email))
    user = user_row.scalar_one_or_none()
    if not user:
        return "Profile not found"

    profile_row, prefs_row = await asyncio.gather(
        db.execute(select(Profile).where(Profile.user_id == user.id)),
        db.execute(select(ProfilePreferences).where(ProfilePreferences.user_id == user.id)),
    )
    profile = profile_row.scalar_one_or_none()
    prefs   = prefs_row.scalar_one_or_none()

    if not profile:
        return "No profile data"

    summary = (
        f"{profile.full_name}, {profile.degree_level} in {profile.degree_field} "
        f"({profile.university}), CGPA {profile.cgpa}/{profile.cgpa_scale}, "
        f"{profile.english_test} {profile.english_score}, "
        f"graduating {profile.graduation_month}/{profile.graduation_year}"
    )
    if prefs:
        countries = ", ".join((prefs.preferred_countries or [])[:5])
        summary += (
            f" | Countries: {countries}"
            f" | Max tuition: €{prefs.max_tuition_eur_per_year}/yr"
            f" | Scholarship required: {prefs.scholarship_required}"
        )
    return summary


async def _load_opportunities(db: AsyncSession, user_id: str) -> str:
    result = await db.execute(
        select(Opportunity)
        .options(selectinload(Opportunity.programme).options(selectinload(Programme.university)))
        .where(Opportunity.user_id == user_id)
        .order_by(desc(Opportunity.total_score))
        .limit(20)  # keep context small — 20 is enough for any question
    )
    opps = result.scalars().all()
    if not opps:
        return "No opportunities discovered yet."

    lines = []
    for opp in opps:
        prog = opp.programme
        uni  = prog.university if prog else None
        tuition = f"€{prog.tuition_eur_per_year}/yr" if prog and prog.tuition_eur_per_year is not None else "?"
        lines.append(
            f"- {prog.name if prog else '?'} @ {uni.name if uni else '?'} ({uni.country if uni else '?'})"
            f" | score={opp.total_score:.0f} | {opp.eligibility_status}"
            f" | {tuition} | deadline={opp.application_deadline or 'unknown'}"
        )
    return "\n".join(lines)


async def _load_pipeline(db: AsyncSession, user_id: str) -> str:
    result = await db.execute(
        select(Application.status, Application.opportunity_id)
        .where(Application.user_id == user_id)
    )
    rows = result.all()
    if not rows:
        return "No applications tracked yet."

    counts: dict[str, int] = {}
    for status, _ in rows:
        counts[status] = counts.get(status, 0) + 1
    return " | ".join(f"{s}: {n}" for s, n in counts.items())


async def ask_assistant(
    question: str,
    db: AsyncSession,
    user_email: str | None = None,
) -> str:
    """
    Answer a question about the user's opportunities.
    All DB queries run concurrently; LLM call is non-blocking.
    """
    from app.config import get_settings
    resolved_email = user_email or get_settings().user_email
    logger.info("assistant_question", question=question[:80])

    # Resolve user_id first (needed for the two data queries)
    from app.models.user import User
    user_row = await db.execute(select(User).where(User.email == resolved_email))
    user = user_row.scalar_one_or_none()
    if not user:
        return "Couldn't find your profile. Make sure the backend has your data seeded."

    # Run profile + opportunities + pipeline queries concurrently
    profile_summary, opportunities_data, pipeline_data = await asyncio.gather(
        _load_profile(db, resolved_email),
        _load_opportunities(db, str(user.id)),
        _load_pipeline(db, str(user.id)),
    )

    prompt = _SYSTEM_PROMPT.format(
        profile_summary=profile_summary,
        opportunities_data=opportunities_data,
        pipeline_data=pipeline_data,
        question=question,
    )

    try:
        # async — never blocks the event loop
        answer = await call_llm_async(
            prompt=prompt,
            model="fast",
            temperature=0.3,
            max_tokens=1024,   # assistant answers rarely need more than this
            task_name="assistant",
        )
        logger.info("assistant_answered", chars=len(answer))
        return answer
    except LLMError as e:
        logger.error("assistant_llm_failed", error=str(e))
        if e.retryable:
            return "I'm being rate-limited right now. Try again in a minute."
        return f"Couldn't answer right now: {e}"
