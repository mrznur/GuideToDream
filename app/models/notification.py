"""
app/models/notification.py
──────────────────────────
Notification log — every notification sent to the user is recorded here.

Why log notifications?
1. Suppression: "has the user been notified about this opportunity
   in the last 7 days?" — requires querying notification history
2. Audit: what did the agent decide to tell me, and when?
3. Analytics: are notifications being acted on?
4. Debugging: why did / didn't I get a notification?
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL")
    )

    # Type of notification
    # "new_opportunity" | "deadline_reminder" | "material_change" |
    # "application_reminder" | "application_question"
    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Channel used to deliver this notification
    # "telegram" | "email" | "console" (development)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # What did the user do after receiving this?
    # "applied" | "snoozed" | "dismissed" | "shortlisted" | None (no response yet)
    action_taken: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Notification type={self.notification_type} channel={self.channel}>"
