"""
app/models/source.py
────────────────────
Source tracking — every important fact traces back to a source.

This is one of the most important tables in the system.
Without it, the agent is just producing claims with no evidence.
With it, you can always ask "why did you say that?" and get a URL.

Source tiers (from architecture doc):
  1 = Official university website
  2 = Official government / scholarship organization
  3 = Official application portal
  4 = Trusted educational database (DAAD, Mastersportal, etc.)
  5 = Blog / forum / social media
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # "university_official", "gov_official", "app_portal", "edu_database", "blog"

    # Tier 1-5 per architecture doc
    tier: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str | None] = mapped_column(Text)

    # SHA256 hash of the page content at time of retrieval.
    # If we re-fetch and the hash changes, something on the page changed.
    # This is how we detect: deadline updated, tuition changed, etc.
    raw_content_hash: Mapped[str | None] = mapped_column(String(64))

    # Confidence in information quality from this source (0.0–1.0)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Source tier={self.tier} url={self.url[:60]}>"
