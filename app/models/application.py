"""
app/models/application.py
─────────────────────────
Application pipeline tracker.

Tracks where you are in the application process for each opportunity.

State machine:
  discovered → shortlisted → preparing → applied → [interview] → accepted
                                                               → rejected
                                                               → withdrawn

Why a state machine?
Because application status has defined valid transitions.
You can't go from "discovered" directly to "accepted".
Modeling it as a state machine makes invalid transitions detectable
and allows the assistant to ask smart questions:
  "You've been preparing for TU Berlin for 30 days. Have you applied?"
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Valid application statuses
APPLICATION_STATUSES = [
    "discovered",    # system found it, not yet reviewed by user
    "shortlisted",   # user has reviewed and wants to track it
    "preparing",     # user is actively preparing the application
    "applied",       # user has submitted the application
    "interview",     # user has been invited to interview
    "accepted",      # user has received an offer
    "rejected",      # application was rejected
    "withdrawn",     # user decided not to proceed
]


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one application record per opportunity
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="discovered"
    )

    # When did the user actually submit the application?
    applied_at: Mapped[date | None] = mapped_column(Date)

    # Free text notes (interview prep, document checklist, etc.)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship
    opportunity: Mapped["Opportunity"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Opportunity", back_populates="application"
    )

    def __repr__(self) -> str:
        return f"<Application status={self.status} opportunity_id={self.opportunity_id}>"
