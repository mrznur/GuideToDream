"""
app/models/profile.py
─────────────────────
Academic profile and preferences for the user.

Two separate tables:
- Profile: stable academic facts (degree, CGPA, university, English score)
- ProfilePreferences: search preferences that change more often
  (target countries, budget, fields of interest)

Why separate? Because profile facts change rarely (you defend your thesis
once), but preferences change often (you add a new country, adjust budget).
Keeping them separate makes queries cleaner and updates safer.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Personal
    full_name: Mapped[str | None] = mapped_column(String(255))
    nationality: Mapped[str | None] = mapped_column(String(100))

    # Academic
    degree_level: Mapped[str | None] = mapped_column(
        String(50)
    )  # "Bachelor", "Master"
    degree_field: Mapped[str | None] = mapped_column(
        String(255)
    )  # "Computer Science"
    university: Mapped[str | None] = mapped_column(String(255))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    graduation_month: Mapped[int | None] = mapped_column(Integer)  # 1-12
    is_graduated: Mapped[bool] = mapped_column(Boolean, default=False)

    # CGPA — stored as two separate numbers so we can normalize
    # e.g. 2.80 / 4.00 → we can compare across scales
    cgpa: Mapped[float | None] = mapped_column(Numeric(4, 2))  # e.g. 2.80
    cgpa_scale: Mapped[float | None] = mapped_column(Numeric(4, 2))  # e.g. 4.00

    # English proficiency
    english_test: Mapped[str | None] = mapped_column(
        String(50)
    )  # "IELTS", "TOEFL", None
    english_score: Mapped[float | None] = mapped_column(Numeric(4, 1))  # e.g. 7.0
    english_test_year: Mapped[int | None] = mapped_column(Integer)

    # Summary for LLM context (the professional summary from your CV)
    professional_summary: Mapped[str | None] = mapped_column(Text)

    # Thesis / research
    thesis_title: Mapped[str | None] = mapped_column(Text)
    thesis_summary: Mapped[str | None] = mapped_column(Text)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")  # type: ignore[name-defined] # noqa: F821

    @property
    def cgpa_normalized(self) -> float | None:
        """Returns CGPA as a fraction of scale (0.0–1.0) for comparison."""
        if self.cgpa is not None and self.cgpa_scale:
            return float(self.cgpa) / float(self.cgpa_scale)
        return None

    def __repr__(self) -> str:
        return f"<Profile user_id={self.user_id} cgpa={self.cgpa}/{self.cgpa_scale}>"


class ProfilePreferences(Base):
    __tablename__ = "profile_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Country preferences
    # PostgreSQL ARRAY type — stores a list of strings in a single column
    # More efficient than a separate junction table for simple string lists
    preferred_countries: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    avoided_countries: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )

    # Financial preferences
    max_tuition_eur_per_year: Mapped[int | None] = mapped_column(
        Integer
    )  # None = no limit (we'll treat as 10000 in scoring)
    scholarship_required: Mapped[bool] = mapped_column(Boolean, default=True)
    stipend_preferred: Mapped[bool] = mapped_column(Boolean, default=True)

    # Academic target
    degree_level_targets: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default='{"Master"}', nullable=False
    )
    fields_of_interest: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )

    # Skills — JSONB allows flexible structure:
    # {"python": "advanced", "pytorch": "intermediate", ...}
    # We use JSONB (binary JSON) rather than JSON because:
    # - JSONB is indexed and queryable
    # - JSON is stored as plain text (slower for queries)
    skills: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # Work experience highlights (for LLM context)
    work_experience_summary: Mapped[str | None] = mapped_column(Text)

    # Notable projects (list of project names/summaries)
    notable_projects: Mapped[list] = mapped_column(
        JSONB, server_default="[]", nullable=False
    )

    # Free-text notes about preferences
    notes: Mapped[str | None] = mapped_column(Text)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="preferences")  # type: ignore[name-defined] # noqa: F821

    def __repr__(self) -> str:
        return f"<ProfilePreferences user_id={self.user_id}>"
