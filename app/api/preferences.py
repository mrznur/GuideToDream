"""
app/api/preferences.py
───────────────────────
Read and update the user's search preferences.

Endpoints:
  GET  /preferences          Get current preferred + avoided countries
  PATCH /preferences/countries  Update preferred/avoided country lists
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.profile import ProfilePreferences
from app.models.user import User

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferencesOut(BaseModel):
    preferred_countries: list[str]
    avoided_countries: list[str]
    fields_of_interest: list[str]
    scholarship_required: bool
    max_tuition_eur_per_year: int | None


class UpdateCountriesRequest(BaseModel):
    preferred_countries: list[str] | None = None
    avoided_countries: list[str] | None = None


async def _get_prefs(db: AsyncSession) -> ProfilePreferences:
    email = get_settings().user_email
    user_r = await db.execute(select(User).where(User.email == email))
    user = user_r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefs_r = await db.execute(
        select(ProfilePreferences).where(ProfilePreferences.user_id == user.id)
    )
    prefs = prefs_r.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs


@router.get("", response_model=PreferencesOut)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """Get the user's current search preferences."""
    prefs = await _get_prefs(db)
    return PreferencesOut(
        preferred_countries=list(prefs.preferred_countries or []),
        avoided_countries=list(prefs.avoided_countries or []),
        fields_of_interest=list(prefs.fields_of_interest or []),
        scholarship_required=prefs.scholarship_required,
        max_tuition_eur_per_year=prefs.max_tuition_eur_per_year,
    )


@router.patch("/countries", response_model=PreferencesOut)
async def update_countries(
    body: UpdateCountriesRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update preferred and/or avoided country lists.

    - preferred_countries: countries to actively search in
    - avoided_countries: countries to exclude from all future research
    """
    prefs = await _get_prefs(db)

    if body.preferred_countries is not None:
        # Normalise: strip whitespace, title-case for consistency
        prefs.preferred_countries = [c.strip().title() for c in body.preferred_countries if c.strip()]

    if body.avoided_countries is not None:
        prefs.avoided_countries = [c.strip().title() for c in body.avoided_countries if c.strip()]

    await db.commit()
    await db.refresh(prefs)

    return PreferencesOut(
        preferred_countries=list(prefs.preferred_countries or []),
        avoided_countries=list(prefs.avoided_countries or []),
        fields_of_interest=list(prefs.fields_of_interest or []),
        scholarship_required=prefs.scholarship_required,
        max_tuition_eur_per_year=prefs.max_tuition_eur_per_year,
    )
