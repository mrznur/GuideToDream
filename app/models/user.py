"""
app/models/user.py
──────────────────
User model — the single user of this system (you).

Even though this is a personal tool, we model a proper User entity.
Why? Because:
1. Every piece of data (profile, opportunities, applications) needs
   an owner. Foreign keys to users.id enforce data integrity.
2. When we add the API, we need to authenticate requests.
3. Good habit — design for correctness even in personal projects.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # UUID primary key — better than auto-increment integers because:
    # - Safe to generate client-side without a DB roundtrip
    # - No information leakage (can't guess "there are 1000 users")
    # - Works correctly when merging data from multiple environments
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships — SQLAlchemy uses these to JOIN tables automatically
    # 'back_populates' creates a two-way link:
    #   user.profile → gives you the profile
    #   profile.user → gives you back the user
    profile: Mapped["Profile"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "Profile", back_populates="user", uselist=False
    )
    preferences: Mapped["ProfilePreferences"] = relationship(  # type: ignore[name-defined] # noqa: F821
        "ProfilePreferences", back_populates="user", uselist=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
