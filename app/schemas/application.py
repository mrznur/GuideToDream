"""
app/schemas/application.py
───────────────────────────
Pydantic schemas for the application tracker API.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.application import APPLICATION_STATUSES


class ApplicationCreate(BaseModel):
    """Create a new application record (usually auto-created on opportunity discovery)."""
    opportunity_id: UUID
    status: str = "discovered"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in APPLICATION_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of: {APPLICATION_STATUSES}")
        return v


class ApplicationUpdate(BaseModel):
    """Update an existing application — all fields optional."""
    status: str | None = None
    applied_at: date | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in APPLICATION_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of: {APPLICATION_STATUSES}")
        return v


class ApplicationOut(BaseModel):
    """Application record returned by the API."""
    id: UUID
    opportunity_id: UUID
    status: str
    applied_at: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StatusTransitionRequest(BaseModel):
    """
    Request to transition an application to a new status.
    Includes validation of legal transitions.
    """
    new_status: str
    notes: str | None = None

    # Legal state transitions
    TRANSITIONS: dict[str, list[str]] = {
        "discovered":   ["shortlisted", "withdrawn"],
        "shortlisted":  ["preparing", "withdrawn"],
        "preparing":    ["applied", "withdrawn"],
        "applied":      ["interview", "accepted", "rejected", "withdrawn"],
        "interview":    ["accepted", "rejected", "withdrawn"],
        "accepted":     [],   # terminal
        "rejected":     [],   # terminal
        "withdrawn":    [],   # terminal
    }

    def is_valid_transition(self, current_status: str) -> bool:
        allowed = self.TRANSITIONS.get(current_status, [])
        return self.new_status in allowed

    @field_validator("new_status")
    @classmethod
    def validate_new_status(cls, v: str) -> str:
        if v not in APPLICATION_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {APPLICATION_STATUSES}")
        return v
