"""
app/services/profile_service.py
────────────────────────────────
Loads the user profile from the database and converts it to a
UserProfileSnapshot for use by the eligibility and scoring engines.

WHY A SEPARATE SERVICE?
The eligibility and scoring engines work with UserProfileSnapshot —
a plain Python dataclass with no database dependencies.
This service is the bridge: it reads from SQLAlchemy ORM models
and produces the clean snapshot that the engines expect.

This is called the ADAPTER PATTERN:
  Database model (ORM) → ProfileService → UserProfileSnapshot (plain data)

The engines don't know SQLAlchemy exists. They just get a dataclass.
This makes the engines testable without a database (as you saw in M5/M6).
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile, ProfilePreferences
from app.models.user import User
from app.services.eligibility_service import UserProfileSnapshot

logger = structlog.get_logger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a user record by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_profile_snapshot(
    db: AsyncSession,
    user_email: str,
) -> UserProfileSnapshot | None:
    """
    Load a user's profile and preferences from the database,
    and return a UserProfileSnapshot for use by the engines.

    Returns None if the user or profile doesn't exist.
    """
    # Load user
    user_result = await db.execute(select(User).where(User.email == user_email))
    user = user_result.scalar_one_or_none()
    if not user:
        logger.error("profile_load_failed", reason="user_not_found", email=user_email)
        return None

    # Load profile
    profile_result = await db.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        logger.error("profile_load_failed", reason="profile_not_found", user_id=str(user.id))
        return None

    # Load preferences
    prefs_result = await db.execute(
        select(ProfilePreferences).where(ProfilePreferences.user_id == user.id)
    )
    prefs = prefs_result.scalar_one_or_none()
    if not prefs:
        logger.warning("profile_preferences_missing", user_id=str(user.id))
        # Use defaults if no preferences set
        prefs = ProfilePreferences(user_id=user.id)

    snapshot = UserProfileSnapshot(
        cgpa=float(profile.cgpa or 0),
        cgpa_scale=float(profile.cgpa_scale or 4.0),
        degree_level=profile.degree_level or "Bachelor",
        degree_field=profile.degree_field or "Computer Science",
        nationality=profile.nationality or "Unknown",
        english_test=profile.english_test,
        english_score=float(profile.english_score) if profile.english_score else None,
        max_tuition_eur_per_year=prefs.max_tuition_eur_per_year or 10000,
        scholarship_required=prefs.scholarship_required or True,
        preferred_countries=list(prefs.preferred_countries or []),
        avoided_countries=list(prefs.avoided_countries or []),
        graduation_year=profile.graduation_year,
        graduation_month=profile.graduation_month,
        fields_of_interest=list(prefs.fields_of_interest or []),
        skills=dict(prefs.skills or {}),
        notable_projects=list(prefs.notable_projects or []),
    )

    logger.info(
        "profile_loaded",
        user_email=user_email,
        cgpa=f"{snapshot.cgpa}/{snapshot.cgpa_scale}",
        countries=len(snapshot.preferred_countries),
        interests=len(snapshot.fields_of_interest),
    )

    return snapshot
