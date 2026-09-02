"""
app/agents/discovery_agent.py
──────────────────────────────
Generates targeted web search queries from the user's profile.

THIS IS ONE OF THE LEGITIMATE LLM USE CASES.

Why use an LLM here instead of hardcoded queries?
Because good search queries require understanding the nuances of:
  - Your specific background (CS + LLM research)
  - Which European countries have free/cheap tuition
  - Which scholarships target Bangladeshi students
  - How to phrase queries to find official university pages
  - Which combination of terms yields programme pages vs blog posts

A hardcoded list would miss opportunities. The LLM generates diverse,
context-aware queries calibrated to your specific profile.

HOWEVER: We still validate and filter the LLM output deterministically.
The LLM suggests queries. We check they're valid strings. We deduplicate.
We add our own base queries as a fallback.
"""

import json

import structlog

from app.services.eligibility_service import UserProfileSnapshot
from app.utils.llm import LLMError, call_llm

logger = structlog.get_logger(__name__)

# Always include these baseline queries regardless of LLM output
# Spread across ALL preferred countries — not just Germany
_BASELINE_QUERIES = [
    # Czech Republic (free tuition for international students)
    "site:cvut.cz master computer science artificial intelligence English admission",
    "site:muni.cz master computer science English taught admission requirements",
    "MSc Computer Science Czech Republic free tuition English 2025 international admission",

    # Netherlands
    "site:uva.nl master artificial intelligence computer science admission requirements",
    "site:tue.nl master computer science artificial intelligence admission",
    "MSc Artificial Intelligence Netherlands 2025 English taught tuition international",

    # Poland (very low tuition)
    "site:pw.edu.pl master computer science English admission 2025",
    "MSc Computer Science Poland 2025 English taught tuition fee international students",

    # Hungary (Stipendium Hungaricum scholarship)
    "Stipendium Hungaricum 2025 computer science artificial intelligence Bangladesh",
    "MSc Computer Science Hungary Budapest English 2025 tuition scholarship",

    # Finland (free tuition + scholarships)
    "site:aalto.fi master computer science artificial intelligence admission 2025",
    "MSc Computer Science Finland 2025 English taught free tuition international",

    # Austria
    "site:tuwien.ac.at master computer science informatics English admission",
    "MSc Computer Science Austria Vienna 2025 English taught tuition",

    # Norway (free tuition)
    "site:uio.no master informatics computer science English admission 2025",
    "MSc Computer Science Norway 2025 free tuition English international students",

    # Sweden
    "site:kth.se master computer science machine learning admission 2025",
    "MSc Artificial Intelligence Sweden 2025 English taught tuition scholarship",

    # Denmark
    "site:dtu.dk master computer science artificial intelligence English admission 2025",

    # Scholarships specifically for Bangladesh (non-German)
    "Erasmus Mundus scholarship computer science AI 2025 open Bangladesh",
    "Swedish Institute scholarship computer science Bangladesh 2025",
    "Stipendium Hungaricum 2025 computer science artificial intelligence Bangladesh",
]

# Countries permanently excluded — never generate queries for these
_EXCLUDED_COUNTRIES = {"germany", "german"}

_QUERY_GENERATION_PROMPT = """You are helping a student find European Master's programmes.

Generate 10 targeted web search queries to find relevant MSc programmes and scholarships.
Each query should be designed to find OFFICIAL UNIVERSITY PAGES or SCHOLARSHIP PORTALS.

Student profile:
- Degree: {degree_level} in {degree_field} from {nationality}
- CGPA: {cgpa}/{cgpa_scale} (note: below average for competitive programmes)
- English: {english_test} {english_score}
- Fields of interest: {interests}
- Target countries: {countries}
- Financial situation: needs free/low-cost tuition or scholarship
- Key strength: {thesis_note}

Generate queries that:
1. Find programmes with holistic admission (not just GPA-based)
2. Target countries with free/cheap tuition for international students
3. Find scholarships specifically for South Asian / Bangladeshi students
4. Find programmes where the student's AI/LLM background is valued
5. Mix different angles: by country, by field, by scholarship type

IMPORTANT: Do NOT generate queries for Germany or German universities under any circumstances.

Return ONLY a JSON array of 10 query strings. No explanation, just the array:
["query 1", "query 2", ...]"""


def generate_search_queries(
    profile: UserProfileSnapshot,
    max_queries: int = 15,
) -> list[str]:
    """
    Generate a list of web search queries tailored to the user's profile.

    Combines LLM-generated queries with baseline queries.
    Always returns at least the baseline queries even if LLM fails.

    Args:
        profile: User's profile snapshot
        max_queries: Maximum number of queries to return

    Returns:
        List of search query strings, deduplicated
    """
    queries = list(_BASELINE_QUERIES)  # start with reliable baseline

    # Build context for the LLM
    thesis_note = "Strong AI/LLM research thesis (Tree-of-Thoughts, 89% accuracy)"
    if profile.notable_projects:
        names = [p.get("name", "") for p in profile.notable_projects if isinstance(p, dict)]
        if names:
            thesis_note = f"Notable projects: {', '.join(names[:2])}"

    prompt = _QUERY_GENERATION_PROMPT.format(
        degree_level=profile.degree_level,
        degree_field=profile.degree_field,
        nationality=profile.nationality,
        cgpa=profile.cgpa,
        cgpa_scale=profile.cgpa_scale,
        english_test=profile.english_test or "IELTS",
        english_score=profile.english_score or 7.0,
        interests=", ".join(profile.fields_of_interest[:5]) if profile.fields_of_interest else "AI, ML, CS",
        countries=", ".join(profile.preferred_countries[:6]) if profile.preferred_countries else "Netherlands, Czech Republic",
        thesis_note=thesis_note,
    )

    try:
        raw = call_llm(prompt, model="fast", temperature=0.7, task_name="query_generation")

        # Extract JSON array from response
        raw = raw.strip()
        # Strip markdown fences
        if "```" in raw:
            import re
            raw = re.sub(r"```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```", "", raw)
            raw = raw.strip()

        # Find the JSON array
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > 0:
            llm_queries = json.loads(raw[start:end])
            # Validate: must be list of strings
            if isinstance(llm_queries, list):
                valid = [
                    q for q in llm_queries
                    if isinstance(q, str)
                    and len(q) > 10
                    # Hard exclude Germany regardless of what LLM generates
                    and not any(exc in q.lower() for exc in _EXCLUDED_COUNTRIES)
                ]
                queries.extend(valid)
                logger.info(
                    "query_generation_completed",
                    llm_queries=len(valid),
                    total=len(queries),
                )

    except (LLMError, json.JSONDecodeError, Exception) as e:
        logger.warning(
            "query_generation_llm_failed",
            error=str(e),
            fallback="using baseline queries only",
        )
        # Baseline queries are already in the list — continue gracefully

    # Deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        q_normalized = q.lower().strip()
        if q_normalized not in seen:
            seen.add(q_normalized)
            unique_queries.append(q)

    result = unique_queries[:max_queries]
    logger.info("queries_ready", count=len(result))
    return result
