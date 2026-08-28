"""
app/models/programme.py
────────────────────────
University, Programme, and ProgrammeRequirement models.

Key design decisions:
- University is its own table because many programmes share a university
- ProgrammeRequirement is separate from Programme so we can:
  a) store multiple requirements per programme
  b) track confidence and source per requirement individually
  c) flag strict vs soft requirements per field
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
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class University(Base):
    __tablename__ = "universities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    official_url: Mapped[str | None] = mapped_column(Text)

    # QS World University Ranking (null if unranked or unknown)
    qs_rank: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship — one university has many programmes
    programmes: Mapped[list["Programme"]] = relationship(
        "Programme", back_populates="university"
    )

    def __repr__(self) -> str:
        return f"<University {self.name}, {self.country}>"


class Programme(Base):
    __tablename__ = "programmes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    degree_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "MSc", "MA"
    field: Mapped[str] = mapped_column(String(255), nullable=False)

    # Instruction language — "English", "German", "English/German"
    language: Mapped[str] = mapped_column(String(100), nullable=False, default="English")

    duration_months: Mapped[int | None] = mapped_column(Integer)  # typically 18 or 24

    # Tuition — stored per year in EUR for consistency
    # None means not yet extracted (not necessarily free)
    tuition_eur_per_year: Mapped[int | None] = mapped_column(Integer)
    tuition_notes: Mapped[str | None] = mapped_column(Text)  # "admin fee only", etc.

    # Intake months — e.g. ["September", "February"] or ["October"]
    intake_months: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )

    # URLs
    official_url: Mapped[str | None] = mapped_column(Text)
    application_portal_url: Mapped[str | None] = mapped_column(Text)

    # Status
    # active: verified and currently accepting applications
    # inactive: programme closed/discontinued
    # unverified: discovered but not yet cross-checked with official source
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="unverified")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    university: Mapped["University"] = relationship("University", back_populates="programmes")
    requirements: Mapped[list["ProgrammeRequirement"]] = relationship(
        "ProgrammeRequirement", back_populates="programme", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Programme {self.degree_type} {self.name}>"


class ProgrammeRequirement(Base):
    """
    A single requirement for a programme.

    Each row is one requirement — we don't cram all requirements into one
    JSON blob because:
    1. We can query by requirement_type (find all programmes with CGPA < 3.0)
    2. Each requirement has its own source, confidence, and strictness flag
    3. We can update individual requirements without touching others

    requirement_type examples:
      "cgpa_min"          → value: "3.0", is_strict: True/False/None
      "degree_field"      → value: "Computer Science or related", is_strict: None
      "english_ielts_min" → value: "6.5", is_strict: True
      "work_experience"   → value: "not required", is_strict: False
      "citizenship"       → value: "EU only", is_strict: True
    """

    __tablename__ = "programme_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    programme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("programmes.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL")
    )

    requirement_type: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)

    # is_strict:
    #   True  → hard cutoff ("minimum 3.0, applications below this are not considered")
    #   False → soft guideline ("normally equivalent to 3.0")
    #   None  → we couldn't determine (LLM flagged ambiguity) — treat as uncertain
    is_strict: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # How confident are we in this extraction? 0.0–1.0
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))

    # The exact text from the source that led to this requirement
    # Crucial for transparency — user can verify the claim
    raw_text: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    programme: Mapped["Programme"] = relationship("Programme", back_populates="requirements")

    def __repr__(self) -> str:
        return f"<Requirement {self.requirement_type}={self.value} strict={self.is_strict}>"
