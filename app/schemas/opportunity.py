"""
app/schemas/opportunity.py
───────────────────────────
Pydantic schemas for opportunity API responses.

These are the shapes of data that the API returns.
They are NOT the database models — they are the public contract.

WHY SEPARATE FROM MODELS?
1. The database model has internal fields (foreign keys, timestamps)
   that don't belong in API responses.
2. You can evolve the DB schema without breaking API clients.
3. You can compute derived fields (days_until_deadline) at response time
   without storing them in the DB.
4. Pydantic validates output automatically — you can't accidentally
   return a None where the client expects a string.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.utils.date_parser import days_until


class RequirementOut(BaseModel):
    requirement_type: str
    value: str | None
    is_strict: bool | None
    confidence: float | None
    raw_text: str | None


class ProgrammeOut(BaseModel):
    id: UUID
    name: str
    degree_type: str
    field: str
    language: str
    duration_months: int | None
    tuition_eur_per_year: int | None
    tuition_notes: str | None
    is_tuition_free: bool = False
    intake_months: list[str]
    official_url: str | None
    application_portal_url: str | None
    status: str
    requirements: list[RequirementOut] = []

    model_config = {"from_attributes": True}


class UniversityOut(BaseModel):
    id: UUID
    name: str
    country: str
    city: str | None
    official_url: str | None
    qs_rank: int | None

    model_config = {"from_attributes": True}


class OpportunityOut(BaseModel):
    id: UUID
    eligibility_status: str
    eligibility_notes: str | None
    total_score: float | None
    score_breakdown: dict | None
    score_explanation: str | None
    application_deadline: date | None
    scholarship_deadline: date | None
    first_discovered_at: datetime
    last_updated_at: datetime
    is_notable_change: bool

    # Nested
    programme: ProgrammeOut | None = None
    university: UniversityOut | None = None

    # Application status (if tracked)
    application_status: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def days_until_deadline(self) -> int | None:
        return days_until(self.application_deadline)

    @computed_field  # type: ignore[misc]
    @property
    def score_label(self) -> str:  # type: ignore[override]
        if self.total_score is None:
            return "Unscored"
        if self.total_score >= 90:
            return "Exceptional match"
        elif self.total_score >= 75:
            return "Strong match"
        elif self.total_score >= 60:
            return "Good match"
        elif self.total_score >= 45:
            return "Moderate match"
        else:
            return "Weak match"

    model_config = {"from_attributes": True}


class OpportunityListOut(BaseModel):
    """Paginated list of opportunities."""
    items: list[OpportunityOut]
    total: int
    page: int
    page_size: int
    has_more: bool
