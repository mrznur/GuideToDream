"""
app/models/scholarship.py
─────────────────────────
Scholarship model.

Scholarships are tracked separately from programmes because:
- One scholarship can apply to many programmes (e.g. DAAD covers
  many German universities)
- One programme can have multiple scholarship options
- Scholarship deadlines are often different from application deadlines
- Scholarship eligibility has its own rules (nationality, field, CGPA)
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Scholarship(Base):
    __tablename__ = "scholarships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL")
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(255))  # "DAAD", "Erasmus+"

    # Scope — which countries/fields does this scholarship apply to?
    country_scope: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    field_scope: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )
    nationality_scope: Mapped[list[str]] = mapped_column(
        ARRAY(String), server_default="{}", nullable=False
    )

    # What does it cover?
    # e.g. "Full tuition + €850/month stipend + travel allowance"
    coverage: Mapped[str | None] = mapped_column(Text)

    # coverage_type: "full" | "partial" | "stipend_only" | "tuition_waiver" | "unknown"
    coverage_type: Mapped[str | None] = mapped_column(String(50))

    official_url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Scholarship {self.name} by {self.provider}>"
