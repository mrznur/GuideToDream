"""
app/services/eligibility_service.py
─────────────────────────────────────
Determines whether the user is eligible for a given programme.

THIS IS PURE DETERMINISTIC PYTHON. No LLM calls.

DESIGN PHILOSOPHY:
The eligibility engine implements a two-phase check:

Phase 1 — Hard Constraints (any failure = INELIGIBLE, stop immediately)
  - Application deadline has passed
  - Citizenship/nationality requirement not met
  - Degree level prerequisite not satisfied
  - English requirement definitively not met
  - CGPA minimum explicitly stated as strict AND definitively not met

Phase 2 — Soft Assessment (produces ELIGIBLE, PROBABLY_ELIGIBLE, or UNCERTAIN)
  - CGPA requirement exists but is ambiguous/soft
  - Degree field is related but not exact
  - English score is close to minimum
  - No requirement stated (assume eligible, flag as unverified)

RESULT HIERARCHY:
  INELIGIBLE > UNCERTAIN > PROBABLY_ELIGIBLE > ELIGIBLE
  (one INELIGIBLE overrides everything)
  (one UNCERTAIN makes the overall result at most UNCERTAIN)

THE CGPA PROBLEM — explained:
Many universities say things like:
  "Minimum 3.0 GPA required"           → is_strict=True  → hard constraint
  "Typically 3.0 GPA or equivalent"     → is_strict=False → soft preference
  "A good academic background expected" → is_strict=None  → uncertain

With your CGPA of 2.80/4.00 = 70%:
  - Hard 3.0 minimum → INELIGIBLE (we cannot hide this)
  - Soft 3.0 "typical" → PROBABLY_ELIGIBLE (flag for manual review)
  - Unknown → UNCERTAIN (flag for manual review)

We NEVER falsely claim experience compensates for a hard CGPA cutoff.
We DO flag when holistic review language suggests CGPA is not the only factor.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

import structlog

from app.agents.extraction_agent import ExtractedProgramme, ExtractedRequirement

logger = structlog.get_logger(__name__)


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    PROBABLY_ELIGIBLE = "probably_eligible"
    UNCERTAIN = "uncertain"
    INELIGIBLE = "ineligible"


@dataclass
class EligibilityFlag:
    """
    A single eligibility finding — one check, one verdict.

    We collect all flags and then combine them into a final verdict.
    This gives us a full audit trail of every check performed.
    """
    check: str                    # what we checked, e.g. "cgpa_minimum"
    status: EligibilityStatus     # result of this specific check
    message: str                  # human-readable explanation
    is_hard_constraint: bool      # True = hard block, False = soft preference
    evidence: str | None = None   # the raw_text from the source that triggered this


@dataclass
class EligibilityResult:
    """
    The complete eligibility assessment for one programme.

    Contains the overall verdict AND every individual check that was performed.
    The user can see exactly why they are or aren't eligible.
    """
    status: EligibilityStatus
    flags: list[EligibilityFlag] = field(default_factory=list)
    summary: str = ""

    @property
    def is_eligible(self) -> bool:
        return self.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.PROBABLY_ELIGIBLE)

    @property
    def hard_blocks(self) -> list[EligibilityFlag]:
        return [f for f in self.flags if f.status == EligibilityStatus.INELIGIBLE and f.is_hard_constraint]

    @property
    def uncertainties(self) -> list[EligibilityFlag]:
        return [f for f in self.flags if f.status == EligibilityStatus.UNCERTAIN]


# ---------------------------------------------------------------------------
# User profile snapshot — a simple container passed to the engine
# This avoids coupling the engine to SQLAlchemy ORM models directly
# ---------------------------------------------------------------------------

@dataclass
class UserProfileSnapshot:
    """
    A plain-data snapshot of the user's profile for eligibility checking.
    Decoupled from SQLAlchemy so the engine is testable without a database.
    """
    cgpa: float                      # e.g. 2.80
    cgpa_scale: float                # e.g. 4.00
    degree_level: str                # "Bachelor"
    degree_field: str                # "Computer Science"
    nationality: str                 # "Bangladeshi"
    english_test: str | None         # "IELTS"
    english_score: float | None      # 7.0
    max_tuition_eur_per_year: int    # 10000
    scholarship_required: bool       # True
    preferred_countries: list[str]   # ["Germany", ...]
    avoided_countries: list[str]     # []
    graduation_year: int | None      # 2026
    graduation_month: int | None     # 5

    @property
    def cgpa_normalized(self) -> float:
        """CGPA as a 0.0-1.0 fraction for cross-scale comparison."""
        if self.cgpa_scale > 0:
            return self.cgpa / self.cgpa_scale
        return 0.0

    @property
    def cgpa_on_4_scale(self) -> float:
        """Approximate CGPA on a 4.0 scale for comparison with common requirements."""
        return self.cgpa_normalized * 4.0


# ---------------------------------------------------------------------------
# Individual check functions
# Each function checks ONE thing and returns ONE EligibilityFlag
# ---------------------------------------------------------------------------

def _check_deadline(deadline: date | None) -> EligibilityFlag:
    """Has the application deadline already passed?"""
    if deadline is None:
        return EligibilityFlag(
            check="application_deadline",
            status=EligibilityStatus.UNCERTAIN,
            message="Application deadline not found. Verify manually before applying.",
            is_hard_constraint=False,
        )
    today = date.today()
    if deadline < today:
        return EligibilityFlag(
            check="application_deadline",
            status=EligibilityStatus.INELIGIBLE,
            message=f"Application deadline {deadline} has already passed (today is {today}).",
            is_hard_constraint=True,
        )
    days_left = (deadline - today).days
    if days_left <= 30:
        return EligibilityFlag(
            check="application_deadline",
            status=EligibilityStatus.ELIGIBLE,
            message=f"Deadline is in {days_left} days ({deadline}). Apply soon.",
            is_hard_constraint=True,
        )
    return EligibilityFlag(
        check="application_deadline",
        status=EligibilityStatus.ELIGIBLE,
        message=f"Deadline: {deadline} ({days_left} days away).",
        is_hard_constraint=True,
    )


def _check_cgpa(req: ExtractedRequirement, profile: UserProfileSnapshot) -> EligibilityFlag:
    """
    Check CGPA requirement against user's CGPA.

    This is the most nuanced check in the system.
    We use is_strict to determine whether to hard-block or soft-flag.
    """
    if req.value is None:
        return EligibilityFlag(
            check="cgpa_minimum",
            status=EligibilityStatus.UNCERTAIN,
            message="CGPA requirement found but value could not be extracted. Verify manually.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    # Try to parse the required CGPA value
    try:
        # Handle values like "3.0", "3.0 out of 4.0", "3.0/4.0"
        raw = req.value.split()[0].replace(",", ".")
        required_cgpa = float(raw)
    except (ValueError, IndexError):
        return EligibilityFlag(
            check="cgpa_minimum",
            status=EligibilityStatus.UNCERTAIN,
            message=f"Could not parse CGPA requirement value: '{req.value}'. Verify manually.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    # Normalize: if required value > 4.0, assume it's on a 10.0 or 100 scale
    # and convert user's CGPA accordingly
    if required_cgpa <= 4.0:
        user_cgpa_comparable = profile.cgpa_on_4_scale
        scale_note = f"(your {profile.cgpa}/{profile.cgpa_scale} = {profile.cgpa_on_4_scale:.2f}/4.0)"
    elif required_cgpa <= 10.0:
        user_cgpa_comparable = profile.cgpa_normalized * 10.0
        scale_note = f"(your {profile.cgpa}/{profile.cgpa_scale} ≈ {user_cgpa_comparable:.1f}/10.0)"
    else:
        # Percentage scale
        user_cgpa_comparable = profile.cgpa_normalized * 100.0
        scale_note = f"(your {profile.cgpa}/{profile.cgpa_scale} ≈ {user_cgpa_comparable:.0f}%)"

    meets_requirement = user_cgpa_comparable >= required_cgpa
    margin = user_cgpa_comparable - required_cgpa

    if meets_requirement:
        return EligibilityFlag(
            check="cgpa_minimum",
            status=EligibilityStatus.ELIGIBLE,
            message=(
                f"CGPA requirement met: required {required_cgpa}, "
                f"you have {user_cgpa_comparable:.2f} {scale_note}. "
                f"Margin: +{margin:.2f}."
            ),
            is_hard_constraint=req.is_strict is True,
            evidence=req.raw_text,
        )

    # User is below the requirement
    if req.is_strict is True:
        # Hard cutoff — definitively ineligible
        return EligibilityFlag(
            check="cgpa_minimum",
            status=EligibilityStatus.INELIGIBLE,
            message=(
                f"Hard CGPA cutoff not met: required {required_cgpa} (strict minimum), "
                f"you have {user_cgpa_comparable:.2f} {scale_note}. "
                f"Shortfall: {abs(margin):.2f}."
            ),
            is_hard_constraint=True,
            evidence=req.raw_text,
        )
    elif req.is_strict is False:
        # Soft guideline — possibly eligible, flag for review
        return EligibilityFlag(
            check="cgpa_minimum",
            status=EligibilityStatus.PROBABLY_ELIGIBLE,
            message=(
                f"CGPA below soft guideline: typical {required_cgpa}, "
                f"you have {user_cgpa_comparable:.2f} {scale_note}. "
                f"This is listed as a guideline, not a hard cutoff. "
                f"Strong thesis/portfolio may compensate — verify with the university."
            ),
            is_hard_constraint=False,
            evidence=req.raw_text,
        )
    else:
        # is_strict is None — we don't know if it's a hard cutoff
        return EligibilityFlag(
            check="cgpa_minimum",
            status=EligibilityStatus.UNCERTAIN,
            message=(
                f"CGPA below stated requirement: required {required_cgpa}, "
                f"you have {user_cgpa_comparable:.2f} {scale_note}. "
                f"Whether this is a strict cutoff is unclear from the source. "
                f"Contact admissions to confirm."
            ),
            is_hard_constraint=False,
            evidence=req.raw_text,
        )


def _check_english(req: ExtractedRequirement, profile: UserProfileSnapshot) -> EligibilityFlag:
    """Check English language requirement against user's test score."""
    req_type = req.requirement_type.lower()

    # Determine which test the requirement is for
    if "ielts" in req_type:
        required_test = "IELTS"
    elif "toefl" in req_type:
        required_test = "TOEFL"
    else:
        required_test = "English"

    if req.value is None:
        return EligibilityFlag(
            check=f"english_{required_test.lower()}",
            status=EligibilityStatus.UNCERTAIN,
            message=f"{required_test} requirement found but score not extractable. Verify manually.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    try:
        required_score = float(req.value.split()[0])
    except (ValueError, IndexError):
        return EligibilityFlag(
            check=f"english_{required_test.lower()}",
            status=EligibilityStatus.UNCERTAIN,
            message=f"Could not parse {required_test} score requirement: '{req.value}'.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    # Check if user has the right test
    user_has_matching_test = (
        profile.english_test is not None
        and required_test.upper() in profile.english_test.upper()
    )

    if not user_has_matching_test:
        # User has a different test — check if we can still assess
        if profile.english_test == "IELTS" and required_test == "TOEFL":
            # Rough equivalence: IELTS 7.0 ≈ TOEFL 94
            # We flag as probably eligible rather than ineligible
            return EligibilityFlag(
                check=f"english_{required_test.lower()}",
                status=EligibilityStatus.PROBABLY_ELIGIBLE,
                message=(
                    f"Requirement is {required_test} {required_score} but you have IELTS {profile.english_score}. "
                    f"IELTS 7.0 is roughly equivalent to TOEFL 94. Verify with admissions."
                ),
                is_hard_constraint=False,
                evidence=req.raw_text,
            )
        return EligibilityFlag(
            check=f"english_{required_test.lower()}",
            status=EligibilityStatus.UNCERTAIN,
            message=(
                f"Requirement is {required_test} {required_score}. "
                f"You have {profile.english_test} {profile.english_score}. "
                f"Different tests — verify equivalence with admissions."
            ),
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    if profile.english_score is None:
        return EligibilityFlag(
            check=f"english_{required_test.lower()}",
            status=EligibilityStatus.UNCERTAIN,
            message=f"{required_test} score not on file. Required: {required_score}.",
            is_hard_constraint=False,
        )

    if profile.english_score >= required_score:
        return EligibilityFlag(
            check=f"english_{required_test.lower()}",
            status=EligibilityStatus.ELIGIBLE,
            message=(
                f"{required_test} requirement met: required {required_score}, "
                f"you have {profile.english_score}."
            ),
            is_hard_constraint=True,
            evidence=req.raw_text,
        )
    else:
        shortfall = required_score - profile.english_score
        # Only treat as "close miss" if explicitly NOT strict AND shortfall is tiny
        if req.is_strict is False and shortfall <= 0.5:
            return EligibilityFlag(
                check=f"english_{required_test.lower()}",
                status=EligibilityStatus.PROBABLY_ELIGIBLE,
                message=(
                    f"{required_test} slightly below soft guideline: required {required_score}, "
                    f"you have {profile.english_score} (shortfall: {shortfall:.1f}). "
                    f"Verify with admissions."
                ),
                is_hard_constraint=False,
                evidence=req.raw_text,
            )
        return EligibilityFlag(
            check=f"english_{required_test.lower()}",
            status=EligibilityStatus.INELIGIBLE,
            message=(
                f"{required_test} requirement not met: required {required_score}, "
                f"you have {profile.english_score} (shortfall: {shortfall:.1f})."
            ),
            is_hard_constraint=True,
            evidence=req.raw_text,
        )


def _check_degree_field(req: ExtractedRequirement, profile: UserProfileSnapshot) -> EligibilityFlag:
    """Check if user's degree field satisfies the requirement."""
    if req.value is None:
        return EligibilityFlag(
            check="degree_field",
            status=EligibilityStatus.UNCERTAIN,
            message="Degree field requirement found but not parseable. Verify manually.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    required_field = req.value.lower()
    user_field = profile.degree_field.lower()

    # Exact or near-exact match
    if user_field in required_field or required_field in user_field:
        return EligibilityFlag(
            check="degree_field",
            status=EligibilityStatus.ELIGIBLE,
            message=f"Degree field match: your '{profile.degree_field}' satisfies '{req.value}'.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    # "related" or "equivalent" language — soft match
    if any(word in required_field for word in ["related", "equivalent", "similar", "or"]):
        # Check for related fields
        cs_related = {
            "computer science", "computing", "software engineering",
            "information technology", "information systems", "electrical engineering",
            "electronics", "mathematics", "data science", "artificial intelligence",
            "machine learning", "cybersecurity", "telecommunication"
        }
        user_is_cs_related = any(term in user_field for term in cs_related)
        if user_is_cs_related:
            return EligibilityFlag(
                check="degree_field",
                status=EligibilityStatus.PROBABLY_ELIGIBLE,
                message=(
                    f"Your '{profile.degree_field}' likely qualifies under '{req.value}'. "
                    f"The 'or related' clause typically includes CS/Engineering graduates."
                ),
                is_hard_constraint=False,
                evidence=req.raw_text,
            )

    # No clear match
    if req.is_strict is True:
        return EligibilityFlag(
            check="degree_field",
            status=EligibilityStatus.INELIGIBLE,
            message=(
                f"Degree field mismatch: required '{req.value}', "
                f"you have '{profile.degree_field}'. This appears to be a strict requirement."
            ),
            is_hard_constraint=True,
            evidence=req.raw_text,
        )

    return EligibilityFlag(
        check="degree_field",
        status=EligibilityStatus.UNCERTAIN,
        message=(
            f"Degree field unclear: required '{req.value}', "
            f"you have '{profile.degree_field}'. "
            f"Verify if your background qualifies."
        ),
        is_hard_constraint=False,
        evidence=req.raw_text,
    )


def _check_citizenship(req: ExtractedRequirement, profile: UserProfileSnapshot) -> EligibilityFlag:
    """Check citizenship/nationality requirements."""
    if req.value is None:
        return EligibilityFlag(
            check="citizenship",
            status=EligibilityStatus.UNCERTAIN,
            message="Citizenship requirement found but not extractable. Verify manually.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    req_value_lower = req.value.lower()
    user_nationality_lower = profile.nationality.lower()

    # Check for EU-only restriction
    eu_countries = {
        "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic",
        "denmark", "estonia", "finland", "france", "germany", "greece", "hungary",
        "ireland", "italy", "latvia", "lithuania", "luxembourg", "malta",
        "netherlands", "poland", "portugal", "romania", "slovakia", "slovenia",
        "spain", "sweden"
    }
    if "eu" in req_value_lower or "european union" in req_value_lower or "eea" in req_value_lower:
        user_is_eu = user_nationality_lower in eu_countries
        if not user_is_eu:
            # Check if it's a fee restriction vs hard eligibility block
            if "fee" in (req.raw_text or "").lower() or "tuition" in (req.raw_text or "").lower():
                return EligibilityFlag(
                    check="citizenship",
                    status=EligibilityStatus.PROBABLY_ELIGIBLE,
                    message=(
                        f"EU/EEA fee distinction: as a {profile.nationality} national, "
                        f"you pay non-EU fees. This does not block admission."
                    ),
                    is_hard_constraint=False,
                    evidence=req.raw_text,
                )
            return EligibilityFlag(
                check="citizenship",
                status=EligibilityStatus.INELIGIBLE,
                message=(
                    f"Citizenship restriction: programme requires EU/EEA citizenship. "
                    f"You are {profile.nationality}."
                ),
                is_hard_constraint=True,
                evidence=req.raw_text,
            )

    # Check if user's nationality is explicitly mentioned
    if user_nationality_lower in req_value_lower or "bangladesh" in req_value_lower:
        return EligibilityFlag(
            check="citizenship",
            status=EligibilityStatus.ELIGIBLE,
            message=f"Nationality requirement met: {profile.nationality} explicitly included.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    # Generic "open to all" language
    if any(word in req_value_lower for word in ["all", "international", "worldwide", "open"]):
        return EligibilityFlag(
            check="citizenship",
            status=EligibilityStatus.ELIGIBLE,
            message="Programme open to international students including Bangladesh.",
            is_hard_constraint=False,
            evidence=req.raw_text,
        )

    return EligibilityFlag(
        check="citizenship",
        status=EligibilityStatus.UNCERTAIN,
        message=f"Citizenship/nationality requirement unclear: '{req.value}'. Verify manually.",
        is_hard_constraint=False,
        evidence=req.raw_text,
    )


def _check_tuition(
    tuition_eur: int | None,
    is_tuition_free: bool | None,
    profile: UserProfileSnapshot,
) -> EligibilityFlag:
    """Check if the programme is within the user's budget."""
    if is_tuition_free or tuition_eur == 0:
        return EligibilityFlag(
            check="tuition_budget",
            status=EligibilityStatus.ELIGIBLE,
            message="Free or near-free tuition — matches your top priority.",
            is_hard_constraint=False,
        )

    if tuition_eur is None:
        return EligibilityFlag(
            check="tuition_budget",
            status=EligibilityStatus.UNCERTAIN,
            message="Tuition fee not found. Verify before applying.",
            is_hard_constraint=False,
        )

    if tuition_eur <= profile.max_tuition_eur_per_year:
        return EligibilityFlag(
            check="tuition_budget",
            status=EligibilityStatus.ELIGIBLE,
            message=(
                f"Tuition EUR {tuition_eur:,}/year is within your budget "
                f"of EUR {profile.max_tuition_eur_per_year:,}/year."
            ),
            is_hard_constraint=False,
        )

    if profile.scholarship_required:
        # Over budget, but scholarship required — flag as uncertain (scholarship may cover it)
        return EligibilityFlag(
            check="tuition_budget",
            status=EligibilityStatus.UNCERTAIN,
            message=(
                f"Tuition EUR {tuition_eur:,}/year exceeds your budget of "
                f"EUR {profile.max_tuition_eur_per_year:,}/year. "
                f"A scholarship would be required to cover the gap."
            ),
            is_hard_constraint=False,
        )

    return EligibilityFlag(
        check="tuition_budget",
        status=EligibilityStatus.INELIGIBLE,
        message=(
            f"Tuition EUR {tuition_eur:,}/year exceeds your maximum budget of "
            f"EUR {profile.max_tuition_eur_per_year:,}/year with no scholarship path."
        ),
        is_hard_constraint=True,
    )


# ---------------------------------------------------------------------------
# Main eligibility evaluation function
# ---------------------------------------------------------------------------

def evaluate_eligibility(
    programme: ExtractedProgramme,
    profile: UserProfileSnapshot,
    application_deadline: date | None = None,
) -> EligibilityResult:
    """
    Evaluate whether the user is eligible for a programme.

    Args:
        programme: Extracted programme data (from ExtractionAgent)
        profile: User's profile snapshot
        application_deadline: Parsed date from opportunity (if available)

    Returns:
        EligibilityResult with overall status and per-check flags
    """
    flags: list[EligibilityFlag] = []

    logger.info(
        "eligibility_check_started",
        programme=programme.programme_name,
        university=programme.university_name,
    )

    # ── Phase 1: Deadline check ──────────────────────────────────────────
    deadline = application_deadline
    if deadline is None and programme.application_deadline:
        # Try to parse the deadline string
        from app.utils.date_parser import parse_date_safe
        deadline = parse_date_safe(programme.application_deadline)

    flags.append(_check_deadline(deadline))

    # ── Phase 2: Tuition budget ──────────────────────────────────────────
    flags.append(
        _check_tuition(
            programme.tuition_eur_per_year,
            programme.is_tuition_free,
            profile,
        )
    )

    # ── Phase 3: Process each extracted requirement ──────────────────────
    for req in programme.requirements:
        req_type = req.requirement_type.lower()

        if req_type == "cgpa_min":
            flags.append(_check_cgpa(req, profile))

        elif req_type in ("english_ielts_min", "english_toefl_min", "english_min"):
            flags.append(_check_english(req, profile))

        elif req_type == "degree_field":
            flags.append(_check_degree_field(req, profile))

        elif req_type == "citizenship":
            flags.append(_check_citizenship(req, profile))

        # work_experience and other types: log but don't block
        # (we don't have enough info to hard-fail on these)

    # ── Phase 4: Combine flags into final verdict ────────────────────────
    result = _combine_flags(flags, programme, profile)

    logger.info(
        "eligibility_check_completed",
        programme=programme.programme_name,
        status=result.status.value,
        hard_blocks=len(result.hard_blocks),
        uncertainties=len(result.uncertainties),
    )

    return result


def _combine_flags(
    flags: list[EligibilityFlag],
    programme: ExtractedProgramme,
    profile: UserProfileSnapshot,
) -> EligibilityResult:
    """
    Combine individual flags into a final EligibilityResult.

    Priority order: INELIGIBLE > UNCERTAIN > PROBABLY_ELIGIBLE > ELIGIBLE
    """
    if not flags:
        # No requirements found — cannot determine eligibility
        return EligibilityResult(
            status=EligibilityStatus.UNCERTAIN,
            flags=[],
            summary=(
                f"No requirements found for {programme.programme_name}. "
                f"Manual verification required."
            ),
        )

    # Hard blocks immediately determine the result
    hard_blocks = [
        f for f in flags
        if f.status == EligibilityStatus.INELIGIBLE and f.is_hard_constraint
    ]
    if hard_blocks:
        block_messages = "; ".join(f.message for f in hard_blocks)
        return EligibilityResult(
            status=EligibilityStatus.INELIGIBLE,
            flags=flags,
            summary=f"Not eligible — hard constraint(s) failed: {block_messages}",
        )

    # Count status types
    statuses = {f.status for f in flags}

    if EligibilityStatus.UNCERTAIN in statuses:
        uncertain_checks = [f.check for f in flags if f.status == EligibilityStatus.UNCERTAIN]
        return EligibilityResult(
            status=EligibilityStatus.UNCERTAIN,
            flags=flags,
            summary=(
                f"Eligibility uncertain for {programme.programme_name} — "
                f"unresolved checks: {', '.join(uncertain_checks)}. "
                f"Manual verification recommended."
            ),
        )

    if EligibilityStatus.PROBABLY_ELIGIBLE in statuses:
        soft_issues = [
            f.message for f in flags
            if f.status == EligibilityStatus.PROBABLY_ELIGIBLE
        ]
        return EligibilityResult(
            status=EligibilityStatus.PROBABLY_ELIGIBLE,
            flags=flags,
            summary=(
                f"Probably eligible for {programme.programme_name}. "
                f"No hard blocks found, but review: {'; '.join(soft_issues)}"
            ),
        )

    # All flags passed
    return EligibilityResult(
        status=EligibilityStatus.ELIGIBLE,
        flags=flags,
        summary=(
            f"Eligible for {programme.programme_name} at {programme.university_name}. "
            f"All checked requirements met."
        ),
    )
