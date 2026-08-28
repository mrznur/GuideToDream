"""
app/agents/assistant_agent.py
──────────────────────────────
Conversational assistant that answers questions about your opportunities.

HOW IT WORKS:
1. User asks a question in plain English
2. We query the database to get relevant structured data
3. We pass the question + data to the LLM
4. The LLM generates a natural language answer based on the actual data

WHY THIS PATTERN (not pure RAG)?
For this use case, the data is small and structured.
We don't need embeddings or vector search.
We can just fetch the relevant records and give them to the LLM directly.
This is simpler, cheaper, and more accurate for structured data.

This pattern is called "Context stuffing" — pack the relevant data
into the LLM context, let it reason over it.

QUESTIONS IT CAN ANSWER:
- "What are my top 10 opportunities?"
- "Which deadlines are coming within 30 days?"
- "Show me the cheapest programmes I'm eligible for"
- "Why did you recommend this programme?"
- "Which scholarships should I prioritize?"
- "What applications am I missing documents for?"
- "Have I applied to [university] yet?"
"""

import json

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.opportunity import Opportunity
from app.models.programme import Programme
from app.utils.llm import LLMError, call_llm

logger = structlog.get_logger(__name__)

_ASSISTANT_SYSTEM_PROMPT = """You are a personal higher education advisor assistant.
You help a student track and evaluate Master's programme opportunities in Europe.

Answer the user's question based ONLY on the data provided below.
Be specific, cite programme names and universities when relevant.
Be honest about limitations — if data is missing, say so.
Keep responses concise but complete.
Format as plain text, not markdown (no **bold** or # headers).

USER PROFILE SUMMARY:
{profile_summary}

OPPORTUNITIES DATA:
{opportunities_data}

APPLICATION PIPELINE:
{pipeline_data}

User question: {question}

Answer:"""


async def _get_context_data(db: AsyncSession, user_email: str) -> tuple[str, str, str]:
    """
    Load relevant data from the database for the assistant's context.
    Returns (profile_summary, opportunities_data, pipeline_data)
    """
    from app.models.user import User
    from app.models.profile import Profile, ProfilePreferences

    # Load user + profile
    user_result = await db.execute(select(User).where(User.email == user_email))
    user = user_result.scalar_one_or_none()
    if not user:
        return "Profile not found", "No opportunities", "No applications"

    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()

    prefs_result = await db.execute(
        select(ProfilePreferences).where(ProfilePreferences.user_id == user.id)
    )
    prefs = prefs_result.scalar_one_or_none()

    profile_summary = "Unknown profile"
    if profile:
        profile_summary = (
            f"Name: {profile.full_name}, "
            f"Degree: {profile.degree_level} in {profile.degree_field} ({profile.university}), "
            f"CGPA: {profile.cgpa}/{profile.cgpa_scale}, "
            f"English: {profile.english_test} {profile.english_score}, "
            f"Graduation: {profile.graduation_month}/{profile.graduation_year}"
        )
        if prefs:
            profile_summary += (
                f", Target countries: {', '.join(prefs.preferred_countries[:5] or [])}, "
                f"Max tuition: EUR {prefs.max_tuition_eur_per_year}/year, "
                f"Scholarship required: {prefs.scholarship_required}"
            )

    # Load top opportunities (limit to 30 to control context size)
    opps_query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.programme).options(
                selectinload(Programme.university),
            )
        )
        .where(Opportunity.user_id == user.id)
        .order_by(desc(Opportunity.total_score))
        .limit(30)
    )
    opps_result = await db.execute(opps_query)
    opps = opps_result.scalars().all()

    opp_lines = []
    for opp in opps:
        prog = opp.programme
        uni = prog.university if prog else None
        opp_lines.append(
            f"- {prog.name if prog else 'Unknown'} @ {uni.name if uni else 'Unknown'} "
            f"({uni.country if uni else '?'}): "
            f"score={opp.total_score:.0f}, "
            f"eligibility={opp.eligibility_status}, "
            f"tuition=EUR {prog.tuition_eur_per_year if prog and prog.tuition_eur_per_year is not None else '?'}/yr, "
            f"deadline={opp.application_deadline or 'unknown'}, "
            f"id={opp.id}"
        )
    opportunities_data = "\n".join(opp_lines) if opp_lines else "No opportunities discovered yet."

    # Load applications
    apps_result = await db.execute(
        select(Application).where(Application.user_id == user.id)
    )
    apps = apps_result.scalars().all()

    pipeline: dict[str, list[str]] = {}
    for app in apps:
        pipeline.setdefault(app.status, []).append(str(app.opportunity_id))

    pipeline_lines = [
        f"- {status}: {len(ids)} application(s)"
        for status, ids in pipeline.items()
    ]
    pipeline_data = "\n".join(pipeline_lines) if pipeline_lines else "No applications tracked yet."

    return profile_summary, opportunities_data, pipeline_data


async def ask_assistant(
    question: str,
    db: AsyncSession,
    user_email: str = "mahmudunmiraz@gmail.com",
) -> str:
    """
    Ask the assistant a question about your opportunities.

    Args:
        question: Natural language question
        db: Database session
        user_email: User's email

    Returns:
        Natural language answer from the LLM
    """
    logger.info("assistant_question", question=question[:80])

    # Load context data from database
    profile_summary, opportunities_data, pipeline_data = await _get_context_data(
        db, user_email
    )

    prompt = _ASSISTANT_SYSTEM_PROMPT.format(
        profile_summary=profile_summary,
        opportunities_data=opportunities_data,
        pipeline_data=pipeline_data,
        question=question,
    )

    try:
        answer = call_llm(
            prompt=prompt,
            model="smart",
            temperature=0.3,
            task_name="assistant",
        )
        logger.info("assistant_answered", chars=len(answer))
        return answer
    except LLMError as e:
        logger.error("assistant_llm_failed", error=str(e))
        return f"I couldn't answer that right now due to an LLM error: {e}"
