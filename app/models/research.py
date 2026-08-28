"""
app/models/research.py
──────────────────────
Research run audit log.

Every time the system runs a research cycle, we log it here.
This gives us:
- Full audit trail of what the agent did
- Cost tracking (LLM calls, API calls)
- Performance monitoring (how long did it take?)
- Error tracking (what failed and why?)
- Debugging (why did the agent behave a certain way on Tuesday?)

A senior engineer would call this "operational telemetry" —
the data that tells you how your system is actually behaving in production.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # "running" | "completed" | "failed" | "partial"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")

    # Metrics
    queries_generated: Mapped[int] = mapped_column(Integer, default=0)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    opportunities_found: Mapped[int] = mapped_column(Integer, default=0)
    opportunities_updated: Mapped[int] = mapped_column(Integer, default=0)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)

    # Cost tracking — in USD
    llm_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))
    search_calls: Mapped[int] = mapped_column(Integer, default=0)

    # Structured error log:
    # [{"stage": "extraction", "url": "...", "error": "...", "timestamp": "..."}]
    errors: Mapped[list | None] = mapped_column(JSONB)

    # Free-text summary or notes about this run
    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<ResearchRun id={self.id} status={self.status}>"
