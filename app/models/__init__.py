"""
app/models/__init__.py
──────────────────────
Imports all models so that:
1. Alembic can discover them via Base.metadata
2. Other modules can do: from app.models import User, Programme, etc.

IMPORTANT: All models must be imported here (even if not used directly)
so that SQLAlchemy's metadata registry knows about them when generating
migrations.
"""

from app.models.application import Application
from app.models.notification import Notification
from app.models.opportunity import Opportunity
from app.models.profile import Profile, ProfilePreferences
from app.models.programme import Programme, ProgrammeRequirement, University
from app.models.research import ResearchRun
from app.models.scholarship import Scholarship
from app.models.source import Source
from app.models.user import User

__all__ = [
    "User",
    "Profile",
    "ProfilePreferences",
    "University",
    "Programme",
    "ProgrammeRequirement",
    "Scholarship",
    "Source",
    "Opportunity",
    "Application",
    "Notification",
    "ResearchRun",
]
