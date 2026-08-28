"""
app/models/opportunity.py
─────────────────────────
Opportunity — a programme (+ optional scholarship) evaluated against
your profile.

This is a computed/derived entity. The same programme can appear as
multiple opportunities if:
- It's paired with different scholarships
- The score changes after you update your profile
- A new research run finds updated information

The opportunity table stores the RESULT of evaluating a programme
against your profile — it's not the programme itself.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    programme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programmes.id", ondelete="SET NULL")
    )
    scholarship_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="SET NULL")
    )

    # -------------------------------------------------------------------------
    # Eligibility
    # -------------------------------------------------------------------------
    # eligible / probably_eligible / uncertain / ineligible
    eligibility_status: Mapped[str] = mapped_column(String(50), nullable=False)
    eligibility_notes: Mapped[str | None] = mapped_column(Text)

    # -------------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------------
    total_score: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 0.00–100.00

    # Stores per-dimension scores as JSON:
    # {
    #   "academic_fit": 0.8,
    #   "financial_fit": 1.0,
    #   "country_preference": 0.9,
    #   "language_feasibility": 1.0,
    #   "scholarship_availability": 0.8,
    #   "deadline_urgency": 0.7,
    #   "portfolio_fit": 0.75,
    #   "reputation": 0.5
    # }
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB)

    # Human-readable explanation of the score
    # e.g. "Strong match: CS background aligns well, free tuition,
    #       IELTS 7.0 exceeds requirement of 6.5. CGPA requirement
    #       unclear — flagged for review."
    score_explanation: Mapped[str | None] = mapped_column(Text)

    # -------------------------------------------------------------------------
    # Deadlines
    # -------------------------------------------------------------------------
    application_deadline: Mapped[date | None] = mapped_column(Date)
    scholarship_deadline: Mapped[date | None] = mapped_column(Date)
    deadline_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL")
    )

    # -------------------------------------------------------------------------
    # Discovery metadata
    # -------------------------------------------------------------------------
    first_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # True if something material changed since last check
    # (deadline updated, tuition changed, scholarship added)
    is_notable_change: Mapped[bool] = mapped_column(Boolean, default=False)

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    programme: Mapped["Programme"] = relationship("Programme")  # type: ignore[name-defined] # noqa: F821
    scholarship: Mapped["Scholarship | None"] = relationship("Scholarship")  # type: ignore[name-defined] # noqa: F821
    application: Mapped["Application | None"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Application", back_populates="opportunity", uselist=False
    )

    def __repr__(self) -> str:
        return (
            f"<Opportunity score={self.total_score} "
            f"eligibility={self.eligibility_status}>"
        )
