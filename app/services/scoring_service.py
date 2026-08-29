"""
app/services/scoring_service.py
────────────────────────────────
Scores an opportunity against the user's profile.

THIS IS PURE DETERMINISTIC PYTHON. No LLM calls.

SCORING PHILOSOPHY:
Each dimension produces a score 0.0-1.0 and a short reason string.
The final score is a weighted average × 100 (0-100 scale).
Every score comes with a human-readable explanation of every dimension.

WHY NOT USE AN LLM FOR SCORING?
Because scoring is fundamentally a comparison of known values against
known preferences. There is nothing ambiguous about:
  - Is EUR 0 tuition within a EUR 10,000 budget? → yes, score 1.0
  - Is Germany in the preferred countries list? → yes, score 1.0
  - Is CGPA 2.80 vs 4.0 normalized? → 0.70

The LLM's job (in the extraction agent) was to turn messy text into
clean structured data. Now that we have clean data, we do math.

SCORE INTERPRETATION:
  90-100: Exceptional match — act on this immediately
  75-89:  Strong match — worth serious consideration
  60-74:  Good match — worth tracking
  45-59:  Moderate match — some concerns, review carefully
  0-44:   Weak match — significant issues

INELIGIBLE PROGRAMMES:
If the eligibility engine returns INELIGIBLE, the score is set to 0
and we don't waste time computing dimensions. The explanation says why.
"""

from dataclasses import dataclass, field
from datetime import date

import structlog

from app.agents.extraction_agent import ExtractedProgramme
from app.services.eligibility_service import (
    EligibilityResult,
    EligibilityStatus,
    UserProfileSnapshot,
)
from app.utils.date_parser import days_until

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Score dimension weights — must sum to 1.0
# ─────────────────────────────────────────────────────────────────────────────

DIMENSION_WEIGHTS: dict[str, float] = {
    "academic_fit":            0.20,
    "financial_fit":           0.20,
    "scholarship_availability": 0.15,
    "english_feasibility":     0.15,
    "country_preference":      0.10,
    "portfolio_fit":           0.10,
    "deadline_urgency":        0.05,
    "programme_reputation":    0.05,
}

assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 0.001, "Weights must sum to 1.0"


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    """Score and reason for a single scoring dimension."""
    name: str
    score: float          # 0.0 - 1.0
    weight: float
    weighted_score: float # score × weight
    reason: str           # human-readable explanation


@dataclass
class ScoreResult:
    """
    Complete scoring result for an opportunity.

    Contains total score, per-dimension breakdown, and
    a human-readable explanation suitable for displaying to the user.
    """
    total_score: float                        # 0.0 - 100.0
    dimensions: list[DimensionScore] = field(default_factory=list)
    explanation: str = ""
    score_label: str = ""                     # "Strong match", "Moderate match", etc.

    @property
    def breakdown_dict(self) -> dict[str, float]:
        """Returns dimension scores as a plain dict for database storage."""
        return {d.name: round(d.score, 3) for d in self.dimensions}

    @classmethod
    def ineligible(cls, reason: str) -> "ScoreResult":
        """Creates a zero-score result for ineligible programmes."""
        return cls(
            total_score=0.0,
            explanation=f"Score not computed — programme is ineligible: {reason}",
            score_label="Ineligible",
        )


def _score_label(score: float) -> str:
    if score >= 90:
        return "Exceptional match"
    elif score >= 75:
        return "Strong match"
    elif score >= 60:
        return "Good match"
    elif score >= 45:
        return "Moderate match"
    else:
        return "Weak match"


# ─────────────────────────────────────────────────────────────────────────────
# Individual dimension scoring functions
# ─────────────────────────────────────────────────────────────────────────────

def _score_academic_fit(
    programme: ExtractedProgramme,
    profile: UserProfileSnapshot,
) -> DimensionScore:
    """
    How well does the programme field match your degree and interests?

    Scoring:
    1.0 — exact field match AND in your interests list
    0.8 — exact field match only
    0.7 — related field (CS/Engineering family) AND in interests
    0.5 — related field
    0.3 — tangentially related
    0.1 — unrelated field
    """
    score = 0.3  # default: unknown/unrelated
    reason_parts = []

    programme_field = (programme.field or "").lower()
    user_field = profile.degree_field.lower()
    interests = [i.lower() for i in profile.fields_of_interest]

    # Check if programme field is in user's interests
    field_in_interests = any(
        interest in programme_field or programme_field in interest
        for interest in interests
    )

    # Exact or near-exact degree match
    if user_field in programme_field or programme_field in user_field:
        score = 0.9 if field_in_interests else 0.8
        reason_parts.append(f"Strong match: your {profile.degree_field} directly aligns with {programme.field}")
        if field_in_interests:
            reason_parts.append("and it's in your stated fields of interest")

    else:
        # Check for CS/Engineering family match
        cs_family = {
            "computer", "computing", "software", "information", "data",
            "artificial intelligence", "machine learning", "ai", "ml",
            "cyber", "network", "digital", "technology", "engineering",
            "mathematics", "statistics", "electronics"
        }
        user_in_cs = any(term in user_field for term in cs_family)
        prog_in_cs = any(term in programme_field for term in cs_family)

        if user_in_cs and prog_in_cs:
            score = 0.7 if field_in_interests else 0.5
            reason_parts.append(
                f"Related field: your {profile.degree_field} is in the "
                f"CS/Engineering family, compatible with {programme.field or 'this programme'}"
            )
            if field_in_interests:
                reason_parts.append("and it's in your stated interests")
        elif field_in_interests:
            score = 0.4
            reason_parts.append(
                f"Partial interest match: {programme.field} is in your interests "
                f"but differs from your degree field ({profile.degree_field})"
            )
        else:
            score = 0.2
            reason_parts.append(
                f"Weak field match: {programme.field} vs your {profile.degree_field}"
            )

    if not programme_field:
        score = 0.4
        reason_parts = ["Programme field not extracted — cannot fully assess academic fit"]

    weight = DIMENSION_WEIGHTS["academic_fit"]
    return DimensionScore(
        name="academic_fit",
        score=round(score, 3),
        weight=weight,
        weighted_score=round(score * weight, 4),
        reason="; ".join(reason_parts) or "Academic fit unknown",
    )


def _score_financial_fit(
    programme: ExtractedProgramme,
    profile: UserProfileSnapshot,
) -> DimensionScore:
    """
    How well does the tuition fit your budget?

    Scoring:
    1.0 — free tuition (best case)
    0.9 — under €500/year (effectively free, admin fees only)
    0.7 — under 50% of max budget
    0.5 — between 50-100% of max budget
    0.2 — over budget but scholarship path exists
    0.0 — over budget, no scholarship context
    """
    tuition = programme.tuition_eur_per_year
    is_free = programme.is_tuition_free
    max_budget = profile.max_tuition_eur_per_year

    if is_free or tuition == 0:
        score = 1.0
        reason = "Free tuition — matches your top financial priority"
    elif tuition is None:
        score = 0.4
        reason = "Tuition not found — verify before applying"
    elif tuition <= 500:
        score = 0.9
        reason = f"Near-free tuition: EUR {tuition:,}/year (admin fees only)"
    elif tuition <= max_budget * 0.5:
        score = 0.75
        reason = f"Well within budget: EUR {tuition:,}/year vs your max EUR {max_budget:,}/year"
    elif tuition <= max_budget:
        ratio = tuition / max_budget
        score = round(0.5 + (1 - ratio) * 0.3, 3)
        reason = f"Within budget: EUR {tuition:,}/year ({int(ratio*100)}% of your max EUR {max_budget:,}/year)"
    else:
        overage = tuition - max_budget
        if profile.scholarship_required:
            score = 0.2
            reason = (
                f"Over budget by EUR {overage:,}/year "
                f"(EUR {tuition:,} vs your max EUR {max_budget:,}). "
                f"Scholarship required to cover the gap."
            )
        else:
            score = 0.1
            reason = (
                f"Over budget: EUR {tuition:,}/year "
                f"exceeds your max EUR {max_budget:,}/year by EUR {overage:,}"
            )

    weight = DIMENSION_WEIGHTS["financial_fit"]
    return DimensionScore(
        name="financial_fit",
        score=score,
        weight=weight,
        weighted_score=round(score * weight, 4),
        reason=reason,
    )


def _score_scholarship(
    has_scholarship: bool,
    scholarship_coverage_type: str | None,
    profile: UserProfileSnapshot,
) -> DimensionScore:
    """
    Is a scholarship available and how comprehensive is it?
    """
    if has_scholarship:
        coverage_scores = {
            "full": 1.0,
            "tuition_waiver": 0.8,
            "partial": 0.6,
            "stipend_only": 0.5,
            "unknown": 0.5,
        }
        score = coverage_scores.get(scholarship_coverage_type or "unknown", 0.5)
        coverage_label = {
            "full": "Full coverage (tuition + stipend)",
            "tuition_waiver": "Tuition waiver",
            "partial": "Partial scholarship",
            "stipend_only": "Stipend only",
            "unknown": "Scholarship available (coverage unknown)",
        }.get(scholarship_coverage_type or "unknown", "Scholarship available")
        reason = f"{coverage_label} attached to this opportunity"
    elif profile.scholarship_required:
        score = 0.1
        reason = "No scholarship found — you require funding to attend"
    else:
        score = 0.4
        reason = "No scholarship attached — may apply independently"

    weight = DIMENSION_WEIGHTS["scholarship_availability"]
    return DimensionScore(
        name="scholarship_availability",
        score=score,
        weight=weight,
        weighted_score=round(score * weight, 4),
        reason=reason,
    )


def _score_english(
    programme: ExtractedProgramme,
    profile: UserProfileSnapshot,
    eligibility: EligibilityResult,
) -> DimensionScore:
    """
    English feasibility — derived from eligibility flags to avoid duplication.
    """
    # Check eligibility flags for English result
    english_flags = [
        f for f in eligibility.flags
        if "english" in f.check.lower() or "ielts" in f.check.lower()
    ]

    if not english_flags:
        # No English requirement found — assume fine (English taught, user has IELTS 7.0)
        if programme.language_of_instruction and "english" in programme.language_of_instruction.lower():
            score = 0.8
            reason = f"English-taught programme; you have IELTS {profile.english_score} (no minimum stated)"
        else:
            score = 0.6
            reason = "Language of instruction unknown — verify requirement"
    else:
        flag = english_flags[0]
        status_scores = {
            EligibilityStatus.ELIGIBLE: 1.0,
            EligibilityStatus.PROBABLY_ELIGIBLE: 0.7,
            EligibilityStatus.UNCERTAIN: 0.5,
            EligibilityStatus.INELIGIBLE: 0.0,
        }
        score = status_scores.get(flag.status, 0.5)
        reason = flag.message

    weight = DIMENSION_WEIGHTS["english_feasibility"]
    return DimensionScore(
        name="english_feasibility",
        score=score,
        weight=weight,
        weighted_score=round(score * weight, 4),
        reason=reason,
    )


def _score_country(
    programme: ExtractedProgramme,
    profile: UserProfileSnapshot,
) -> DimensionScore:
    """Country preference score."""

    # Map known university name keywords to countries
    # This compensates for pages that don't state the country explicitly
    _UNI_COUNTRY_MAP = {
        # Germany
        "berlin": "Germany", "münchen": "Germany", "munich": "Germany",
        "karlsruhe": "Germany", "aachen": "Germany", "freiburg": "Germany",
        "hamburg": "Germany", "heidelberg": "Germany", "tu berlin": "Germany",
        "tum": "Germany", "kit": "Germany", "rwth": "Germany", "lmu": "Germany",
        "technische universität": "Germany", "universität": "Germany",
        "hochschule": "Germany", "ingolstadt": "Germany",
        # Netherlands
        "amsterdam": "Netherlands", "delft": "Netherlands", "eindhoven": "Netherlands",
        "leiden": "Netherlands", "utrecht": "Netherlands", "uva": "Netherlands",
        "tue": "Netherlands", "vu": "Netherlands", "groningen": "Netherlands",
        "tilburg": "Netherlands", "maastricht": "Netherlands",
        # Czech Republic
        "prague": "Czech Republic", "brno": "Czech Republic", "cvut": "Czech Republic",
        "muni": "Czech Republic", "czech": "Czech Republic",
        # Poland
        "warsaw": "Poland", "krakow": "Poland", "wroclaw": "Poland",
        "poznan": "Poland", "polish": "Poland",
        # Hungary
        "budapest": "Hungary", "hungarian": "Hungary", "bme": "Hungary",
        # Finland
        "helsinki": "Finland", "aalto": "Finland", "tampere": "Finland",
        "finnish": "Finland",
        # Austria
        "vienna": "Austria", "wien": "Austria", "graz": "Austria",
        "tuwien": "Austria", "austrian": "Austria",
        # Norway
        "oslo": "Norway", "bergen": "Norway", "trondheim": "Norway",
        "ntnu": "Norway", "norwegian": "Norway",
        # Sweden
        "stockholm": "Sweden", "kth": "Sweden", "gothenburg": "Sweden",
        "chalmers": "Sweden", "swedish": "Sweden", "lund": "Sweden",
        # Denmark
        "copenhagen": "Denmark", "dtu": "Denmark", "danish": "Denmark",
        "aarhus": "Denmark",
    }

    university = (programme.university_name or "").lower()
    programme_name_lower = (programme.programme_name or "").lower()
    combined = university + " " + programme_name_lower

    preferred = [c.lower() for c in profile.preferred_countries]
    avoided = [c.lower() for c in profile.avoided_countries]

    # Detect country from combined text
    detected_country = None
    for keyword, country in _UNI_COUNTRY_MAP.items():
        if keyword in combined:
            detected_country = country
            break

    # Also check if the country is directly mentioned
    for country in profile.preferred_countries + profile.avoided_countries:
        if country.lower() in combined:
            detected_country = country
            break

    if detected_country:
        country_lower = detected_country.lower()
        if country_lower in [a.lower() for a in profile.avoided_countries]:
            return DimensionScore(
                name="country_preference", score=0.0,
                weight=DIMENSION_WEIGHTS["country_preference"],
                weighted_score=0.0,
                reason=f"{detected_country} is in your avoided countries list",
            )
        if country_lower in preferred:
            return DimensionScore(
                name="country_preference", score=1.0,
                weight=DIMENSION_WEIGHTS["country_preference"],
                weighted_score=round(1.0 * DIMENSION_WEIGHTS["country_preference"], 4),
                reason=f"{detected_country} is in your preferred countries list",
            )
        # Detected but not preferred/avoided — neutral
        return DimensionScore(
            name="country_preference", score=0.5,
            weight=DIMENSION_WEIGHTS["country_preference"],
            weighted_score=round(0.5 * DIMENSION_WEIGHTS["country_preference"], 4),
            reason=f"{detected_country} — not in your preferred list but open to it",
        )

    # Country not determinable
    return DimensionScore(
        name="country_preference", score=0.5,
        weight=DIMENSION_WEIGHTS["country_preference"],
        weighted_score=round(0.5 * DIMENSION_WEIGHTS["country_preference"], 4),
        reason="Country not determinable from extracted data — assumed neutral",
    )


def _score_portfolio_fit(
    programme: ExtractedProgramme,
    profile: UserProfileSnapshot,
) -> DimensionScore:
    """
    How well does the user's portfolio and thesis align with the programme?

    This is a heuristic based on keyword matching between the programme field
    and the user's skills/projects. Not perfect but deterministic and fast.
    """
    programme_text = (
        (programme.programme_name or "") + " " +
        (programme.field or "") + " " +
        (programme.university_name or "")
    ).lower()

    skills = list(profile.skills.keys()) if profile.skills else []
    projects = profile.notable_projects if profile.notable_projects else []

    # High-value signals for AI/ML/CS programmes
    ai_ml_signals = {
        "pytorch", "transformers", "llm", "nlp", "machine learning",
        "deep learning", "knowledge distillation", "prompt engineering",
        "fine-tuning", "neural", "ai", "research"
    }
    web_signals = {
        "fastapi", "react", "sqlalchemy", "node", "postgresql",
        "full-stack", "backend", "api", "database"
    }

    # Check thesis relevance
    thesis_relevant = False
    if profile.skills:
        thesis_relevant = any(
            skill in programme_text
            for skill in ["ai", "ml", "llm", "nlp", "machine", "computing", "computer"]
        )

    # Count matching skills
    matching_skills = sum(
        1 for skill in skills
        if skill.lower() in programme_text or
        any(sig in programme_text for sig in ai_ml_signals if skill in sig)
    )

    is_ai_ml_programme = any(
        term in programme_text
        for term in ["artificial intelligence", "machine learning", "data science",
                     "ai", "nlp", "computer science", "computing", "software"]
    )

    if is_ai_ml_programme and thesis_relevant:
        score = 0.9
        reason = (
            "Strong portfolio fit: your Tree-of-Thoughts thesis and LLM/PyTorch experience "
            "directly align with this AI/CS programme"
        )
    elif is_ai_ml_programme:
        score = 0.7
        reason = f"Good portfolio fit: your CS/software background suits this programme"
    elif matching_skills >= 3:
        score = 0.65
        reason = f"Partial portfolio fit: {matching_skills} relevant skills match"
    elif len(projects) > 0:
        score = 0.5
        reason = "Moderate portfolio fit: real-world projects demonstrate practical skills"
    else:
        score = 0.35
        reason = "Portfolio fit unclear — insufficient data to assess"

    weight = DIMENSION_WEIGHTS["portfolio_fit"]
    return DimensionScore(
        name="portfolio_fit",
        score=score,
        weight=weight,
        weighted_score=round(score * weight, 4),
        reason=reason,
    )


def _score_deadline_urgency(
    application_deadline: date | None,
) -> DimensionScore:
    """
    Deadline urgency score.
    Higher score = more urgent = needs attention sooner.
    This isn't about eligibility — it's about prioritization.

    Scoring:
    1.0 — deadline in 7-30 days (urgent, act now)
    0.8 — deadline in 31-60 days (soon)
    0.6 — deadline in 61-90 days (upcoming)
    0.4 — deadline in 91-180 days (future)
    0.2 — deadline > 180 days or unknown (low urgency now)
    0.0 — deadline passed (ineligible, caught by eligibility engine)
    """
    days = days_until(application_deadline)

    if days is None:
        score = 0.3
        reason = "Deadline unknown — verify before planning application timeline"
    elif days < 0:
        score = 0.0
        reason = f"Deadline passed {abs(days)} days ago"
    elif days <= 30:
        score = 1.0
        reason = f"URGENT: deadline in {days} days — apply now"
    elif days <= 60:
        score = 0.8
        reason = f"Deadline in {days} days — start preparing soon"
    elif days <= 90:
        score = 0.6
        reason = f"Deadline in {days} days — upcoming"
    elif days <= 180:
        score = 0.4
        reason = f"Deadline in {days} days — plan ahead"
    else:
        score = 0.2
        reason = f"Deadline in {days} days — low urgency for now"

    weight = DIMENSION_WEIGHTS["deadline_urgency"]
    return DimensionScore(
        name="deadline_urgency",
        score=score,
        weight=weight,
        weighted_score=round(score * weight, 4),
        reason=reason,
    )


def _score_reputation(
    qs_rank: int | None,
) -> DimensionScore:
    """
    Programme/university reputation based on QS World Ranking.

    Scoring:
    1.0 — Top 100
    0.8 — Top 200
    0.65 — Top 500
    0.5 — Ranked (outside top 500)
    0.4 — Unranked (many good European universities aren't in QS)
    """
    if qs_rank is None:
        score = 0.4
        reason = "University not in QS ranking data (many excellent EU universities are unranked)"
    elif qs_rank <= 100:
        score = 1.0
        reason = f"Top 100 globally (QS rank #{qs_rank})"
    elif qs_rank <= 200:
        score = 0.8
        reason = f"Top 200 globally (QS rank #{qs_rank})"
    elif qs_rank <= 500:
        score = 0.65
        reason = f"Top 500 globally (QS rank #{qs_rank})"
    else:
        score = 0.5
        reason = f"Ranked university (QS rank #{qs_rank})"

    weight = DIMENSION_WEIGHTS["programme_reputation"]
    return DimensionScore(
        name="programme_reputation",
        score=score,
        weight=weight,
        weighted_score=round(score * weight, 4),
        reason=reason,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main scoring function
# ─────────────────────────────────────────────────────────────────────────────

def score_opportunity(
    programme: ExtractedProgramme,
    profile: UserProfileSnapshot,
    eligibility: EligibilityResult,
    application_deadline: date | None = None,
    has_scholarship: bool = False,
    scholarship_coverage_type: str | None = None,
    qs_rank: int | None = None,
) -> ScoreResult:
    """
    Score an opportunity on a 0-100 scale with full explanation.

    Args:
        programme: Extracted programme data
        profile: User's profile snapshot
        eligibility: Result from the eligibility engine
        application_deadline: Parsed deadline date
        has_scholarship: Whether a scholarship is attached
        scholarship_coverage_type: Type of scholarship coverage
        qs_rank: University QS world ranking (optional)

    Returns:
        ScoreResult with total score, dimension breakdown, and explanation
    """
    # If ineligible, don't waste computing dimensions
    if eligibility.status == EligibilityStatus.INELIGIBLE:
        reason = "; ".join(f.message for f in eligibility.hard_blocks)
        return ScoreResult.ineligible(reason)

    logger.info(
        "scoring_started",
        programme=programme.programme_name,
        eligibility=eligibility.status.value,
    )

    # Score each dimension
    dimensions = [
        _score_academic_fit(programme, profile),
        _score_financial_fit(programme, profile),
        _score_scholarship(has_scholarship, scholarship_coverage_type, profile),
        _score_english(programme, profile, eligibility),
        _score_country(programme, profile),
        _score_portfolio_fit(programme, profile),
        _score_deadline_urgency(application_deadline),
        _score_reputation(qs_rank),
    ]

    # Calculate weighted total
    total = sum(d.weighted_score for d in dimensions)
    total_score = round(total * 100, 1)

    # Apply eligibility modifier
    # PROBABLY_ELIGIBLE or UNCERTAIN → cap at 80 (uncertainty penalty)
    if eligibility.status == EligibilityStatus.UNCERTAIN:
        total_score = min(total_score, 72.0)
    elif eligibility.status == EligibilityStatus.PROBABLY_ELIGIBLE:
        total_score = min(total_score, 82.0)

    label = _score_label(total_score)

    # Build explanation
    explanation = _build_explanation(
        programme, total_score, label, dimensions, eligibility
    )

    result = ScoreResult(
        total_score=total_score,
        dimensions=dimensions,
        explanation=explanation,
        score_label=label,
    )

    logger.info(
        "scoring_completed",
        programme=programme.programme_name,
        total_score=total_score,
        label=label,
    )

    return result


def _build_explanation(
    programme: ExtractedProgramme,
    total_score: float,
    label: str,
    dimensions: list[DimensionScore],
    eligibility: EligibilityResult,
) -> str:
    """Build a human-readable explanation of the score."""
    lines = [
        f"{label} ({total_score:.0f}/100) — {programme.programme_name or 'Programme'}"
        f" at {programme.university_name or 'Unknown University'}",
        "",
    ]

    # Eligibility summary
    if eligibility.status != EligibilityStatus.ELIGIBLE:
        lines.append(f"Eligibility: {eligibility.status.value.replace('_', ' ').title()}")
        if eligibility.uncertainties:
            uncertain_checks = ", ".join(f.check for f in eligibility.uncertainties)
            lines.append(f"  Unresolved: {uncertain_checks}")
        lines.append("")

    # Top strengths (scores ≥ 0.7)
    strengths = [d for d in dimensions if d.score >= 0.7]
    if strengths:
        lines.append("Strengths:")
        for d in sorted(strengths, key=lambda x: x.score, reverse=True):
            lines.append(f"  + {d.reason}")
        lines.append("")

    # Concerns (scores < 0.5)
    concerns = [d for d in dimensions if d.score < 0.5]
    if concerns:
        lines.append("Concerns:")
        for d in sorted(concerns, key=lambda x: x.score):
            lines.append(f"  - {d.reason}")
        lines.append("")

    # Score breakdown
    lines.append("Score breakdown:")
    for d in dimensions:
        bar = "█" * int(d.score * 10) + "░" * (10 - int(d.score * 10))
        lines.append(
            f"  {d.name.replace('_', ' ').ljust(25)} {bar} {d.score:.2f} × {d.weight:.2f} = {d.weighted_score:.3f}"
        )

    return "\n".join(lines)
