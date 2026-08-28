"""
scripts/seed_profile.py
────────────────────────
One-time script to seed your personal profile into the database.

Run with:
    python scripts/seed_profile.py

This script:
1. Creates the user record (you)
2. Creates your academic profile
3. Creates your search preferences

It is idempotent — running it twice won't create duplicates
(it checks if the user already exists first).

SECURITY NOTE: This script reads your profile from hardcoded values
below. These are not secrets (it's your academic profile, not a password),
but you should still not commit this file with real personal details
if you're working in a public repository.

For a public repo, move sensitive values to .env and read them here.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Profile, ProfilePreferences, User


# ─────────────────────────────────────────────────────────────────────────────
# YOUR PROFILE — edit these values
# ─────────────────────────────────────────────────────────────────────────────

USER_EMAIL = "mahmudunmiraz@gmail.com"

PROFILE_DATA = {
    "full_name": "MD Mahmudun Nur Miraz",
    "nationality": "Bangladeshi",
    "degree_level": "Bachelor",
    "degree_field": "Computer Science",
    "university": "BRAC University",
    "graduation_year": 2026,
    "graduation_month": 5,  # May
    "is_graduated": False,  # Still in progress
    "cgpa": 2.80,
    "cgpa_scale": 4.00,
    "english_test": "IELTS",
    "english_score": 7.0,
    "english_test_year": 2023,
    "professional_summary": (
        "Computer Science graduate with hands-on experience building full-stack "
        "web applications, backend systems, and RESTful APIs using Python, "
        "JavaScript, TypeScript, React, Flask, Node.js, and modern database "
        "technologies. Additionally experienced in applied AI research involving "
        "large language models, prompt engineering, knowledge distillation, and "
        "reasoning systems."
    ),
    "thesis_title": "Tree of Thoughts with CodeAct Pattern",
    "thesis_summary": (
        "Designed and implemented a Tree-of-Thoughts reasoning framework using "
        "the CodeAct pattern, where LLMs generate and execute Python code at each "
        "search step. Achieved 89% puzzle-solving accuracy on Game of 24 benchmark. "
        "Built a teacher-student knowledge distillation pipeline fine-tuning "
        "SmolLM-360M to replicate structured search behavior."
    ),
}

PREFERENCES_DATA = {
    "preferred_countries": [
        "Germany",
        "Netherlands",
        "Czech Republic",
        "Poland",
        "Hungary",
        "Finland",
        "Austria",
        "Norway",
        "Sweden",
        "Denmark",
    ],
    "avoided_countries": [],
    "max_tuition_eur_per_year": 10000,
    "scholarship_required": True,
    "stipend_preferred": True,
    "degree_level_targets": ["Master"],
    "fields_of_interest": [
        "Artificial Intelligence",
        "Machine Learning",
        "Natural Language Processing",
        "Computer Science",
        "Software Engineering",
        "Data Science",
        "LLM Systems",
    ],
    "skills": {
        "python": "advanced",
        "fastapi": "advanced",
        "sqlalchemy": "intermediate",
        "postgresql": "intermediate",
        "pytorch": "intermediate",
        "transformers": "intermediate",
        "react": "intermediate",
        "typescript": "intermediate",
        "llm_engineering": "intermediate",
        "prompt_engineering": "advanced",
        "knowledge_distillation": "intermediate",
    },
    "work_experience_summary": (
        "5 years as private tutor (Math, Science, Programming, IELTS). "
        "Harvard CS50 Transcriber & Translator (2022). "
        "No formal industry employment, but strong portfolio of real-world projects."
    ),
    "notable_projects": [
        {
            "name": "Face Detection System",
            "stack": "FastAPI, PostgreSQL, React, TypeScript",
            "highlight": "Full-stack face recognition with SQLAlchemy + modular architecture",
        },
        {
            "name": "QuickHire",
            "stack": "React, Node.js, Express, MongoDB",
            "highlight": "Full-stack job board with admin dashboard",
        },
        {
            "name": "Thesis: Tree of Thoughts with CodeAct",
            "stack": "Python, PyTorch, DeepSeek API, Gemma 4 31B",
            "highlight": "89% accuracy on Game of 24; distillation pipeline for SmolLM-360M",
        },
    ],
    "notes": (
        "Priority: free/near-free tuition (German public universities, Nordic countries). "
        "Open to up to €10,000/year if scholarship pathway exists. "
        "CGPA is 2.80/4.00 — prefer programmes with holistic review or no hard CGPA cutoff. "
        "Strong thesis and portfolio should be highlighted in matching."
    ),
}

# ─────────────────────────────────────────────────────────────────────────────


async def seed():
    async with AsyncSessionLocal() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == USER_EMAIL))
        user = result.scalar_one_or_none()

        if user:
            print(f"✓ User already exists: {user.email} (id={user.id})")
        else:
            user = User(email=USER_EMAIL)
            db.add(user)
            await db.flush()  # flush to get the user.id without committing yet
            print(f"✓ Created user: {user.email} (id={user.id})")

        # Check if profile already exists
        result = await db.execute(select(Profile).where(Profile.user_id == user.id))
        profile = result.scalar_one_or_none()

        if profile:
            print(f"✓ Profile already exists for user {user.id}")
            # Update existing profile with latest data
            for key, value in PROFILE_DATA.items():
                setattr(profile, key, value)
            print("  → Updated existing profile")
        else:
            profile = Profile(user_id=user.id, **PROFILE_DATA)
            db.add(profile)
            print("✓ Created profile")

        # Check if preferences already exist
        result = await db.execute(
            select(ProfilePreferences).where(ProfilePreferences.user_id == user.id)
        )
        prefs = result.scalar_one_or_none()

        if prefs:
            print(f"✓ Preferences already exist for user {user.id}")
            for key, value in PREFERENCES_DATA.items():
                setattr(prefs, key, value)
            print("  → Updated existing preferences")
        else:
            prefs = ProfilePreferences(user_id=user.id, **PREFERENCES_DATA)
            db.add(prefs)
            print("✓ Created preferences")

        await db.commit()
        print("\n✅ Profile seeded successfully.")
        print(f"   User ID: {user.id}")
        print(f"   Name: {PROFILE_DATA['full_name']}")
        print(f"   CGPA: {PROFILE_DATA['cgpa']}/{PROFILE_DATA['cgpa_scale']}")
        print(f"   IELTS: {PROFILE_DATA['english_score']}")
        print(f"   Target countries: {len(PREFERENCES_DATA['preferred_countries'])} countries")


if __name__ == "__main__":
    asyncio.run(seed())
