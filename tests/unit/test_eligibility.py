"""
tests/unit/test_eligibility.py
────────────────────────────────
Tests for the eligibility engine.

CRITICAL TEST PRINCIPLE:
The most important tests here are FALSE POSITIVE prevention tests.
A false positive = telling you that you're eligible when you're not.
This is worse than a false negative because it wastes your time
and damages trust in the system.

Test categories:
1. CGPA checks — the most nuanced
2. English language checks
3. Deadline checks
4. Degree field checks
5. Citizenship checks
6. Tuition budget checks
7. Combined evaluation (full programme)
8. Date parser
"""

from datetime import date, timedelta

import pytest

from app.agents.extraction_agent import ExtractedProgramme, ExtractedRequirement
from app.services.eligibility_service import (
    EligibilityStatus,
    UserProfileSnapshot,
    _check_cgpa,
    _check_deadline,
    _check_degree_field,
    _check_english,
    _check_tuition,
    evaluate_eligibility,
)
from app.utils.date_parser import days_until, is_passed, is_upcoming, parse_date_safe


# ─────────────────────────────────────────────────────────────────────────────
# Test fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def miraz_profile() -> UserProfileSnapshot:
    """The actual user profile — used for realistic tests."""
    return UserProfileSnapshot(
        cgpa=2.80,
        cgpa_scale=4.00,
        degree_level="Bachelor",
        degree_field="Computer Science",
        nationality="Bangladeshi",
        english_test="IELTS",
        english_score=7.0,
        max_tuition_eur_per_year=10000,
        scholarship_required=True,
        preferred_countries=["Germany", "Netherlands"],
        avoided_countries=[],
        graduation_year=2026,
        graduation_month=5,
    )


def make_cgpa_req(value: str, is_strict: bool | None, raw_text: str = "") -> ExtractedRequirement:
    return ExtractedRequirement(
        requirement_type="cgpa_min",
        value=value,
        is_strict=is_strict,
        confidence=0.9,
        raw_text=raw_text or f"Minimum GPA: {value}",
    )


def make_ielts_req(value: str, is_strict: bool | None = True) -> ExtractedRequirement:
    return ExtractedRequirement(
        requirement_type="english_ielts_min",
        value=value,
        is_strict=is_strict,
        confidence=0.9,
        raw_text=f"IELTS minimum {value} required.",
    )


def make_programme(**kwargs) -> ExtractedProgramme:
    defaults = {
        "programme_name": "MSc Computer Science",
        "university_name": "Test University",
        "degree_type": "MSc",
        "field": "Computer Science",
        "language_of_instruction": "English",
        "confidence_overall": 0.9,
    }
    defaults.update(kwargs)
    return ExtractedProgramme(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# CGPA Tests — most critical
# ─────────────────────────────────────────────────────────────────────────────

class TestCGPA:
    """
    Tests for CGPA eligibility checking.

    KEY RULE: If is_strict=True and user CGPA is below required,
    result MUST be INELIGIBLE. No exceptions. No overrides.
    """

    def test_strict_cutoff_user_below__must_be_ineligible(self, miraz_profile):
        """
        FALSE POSITIVE PREVENTION TEST.
        User CGPA 2.80/4.00. Required 3.0 strict minimum. MUST be INELIGIBLE.
        This is the most important test in the system.
        """
        req = make_cgpa_req("3.0", is_strict=True, raw_text="Minimum GPA of 3.0 required.")
        flag = _check_cgpa(req, miraz_profile)
        assert flag.status == EligibilityStatus.INELIGIBLE
        assert flag.is_hard_constraint is True

    def test_strict_cutoff_user_meets__eligible(self, miraz_profile):
        """User CGPA 2.80 meets requirement of 2.5 strict minimum."""
        req = make_cgpa_req("2.5", is_strict=True)
        flag = _check_cgpa(req, miraz_profile)
        assert flag.status == EligibilityStatus.ELIGIBLE

    def test_strict_cutoff_user_exactly_meets__eligible(self, miraz_profile):
        """User CGPA exactly equals the minimum — should be eligible."""
        req = make_cgpa_req("2.8", is_strict=True)
        flag = _check_cgpa(req, miraz_profile)
        assert flag.status == EligibilityStatus.ELIGIBLE

    def test_soft_guideline_user_below__probably_eligible(self, miraz_profile):
        """
        User below a SOFT guideline (not strict cutoff).
        Should be PROBABLY_ELIGIBLE — not ineligible.
        The message must explain it's a soft guideline.
        """
        req = make_cgpa_req(
            "3.0",
            is_strict=False,
            raw_text="Typically a GPA of 3.0 or equivalent is expected.",
        )
        flag = _check_cgpa(req, miraz_profile)
        assert flag.status == EligibilityStatus.PROBABLY_ELIGIBLE
        assert flag.is_hard_constraint is False
        assert "guideline" in flag.message.lower() or "soft" in flag.message.lower() or "typical" in flag.message.lower()

    def test_unknown_strictness_user_below__uncertain(self, miraz_profile):
        """
        is_strict=None means we don't know if it's a hard cutoff.
        Result must be UNCERTAIN, not INELIGIBLE.
        """
        req = make_cgpa_req(
            "3.0",
            is_strict=None,
            raw_text="A strong academic background is expected.",
        )
        flag = _check_cgpa(req, miraz_profile)
        assert flag.status == EligibilityStatus.UNCERTAIN
        assert flag.is_hard_constraint is False

    def test_no_value__uncertain(self, miraz_profile):
        """Requirement type found but value not extractable."""
        req = make_cgpa_req(None, is_strict=True)
        flag = _check_cgpa(req, miraz_profile)
        assert flag.status == EligibilityStatus.UNCERTAIN

    def test_unparseable_value__uncertain(self, miraz_profile):
        """LLM returned a value we can't parse as a number."""
        req = make_cgpa_req("above average", is_strict=True)
        flag = _check_cgpa(req, miraz_profile)
        assert flag.status == EligibilityStatus.UNCERTAIN

    def test_evidence_stored_in_flag(self, miraz_profile):
        """The raw source text must be stored in the flag for traceability."""
        raw = "Minimum GPA of 3.0 on a 4.0 scale required."
        req = make_cgpa_req("3.0", is_strict=True, raw_text=raw)
        flag = _check_cgpa(req, miraz_profile)
        assert flag.evidence == raw

    def test_cgpa_normalized_correctly(self, miraz_profile):
        """2.80/4.00 = 0.70 normalized = 2.80 on 4.0 scale."""
        assert abs(miraz_profile.cgpa_normalized - 0.70) < 0.01
        assert abs(miraz_profile.cgpa_on_4_scale - 2.80) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# English Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEnglish:

    def test_ielts_met__eligible(self, miraz_profile):
        """User has IELTS 7.0, requirement is 6.5 — met."""
        req = make_ielts_req("6.5")
        flag = _check_english(req, miraz_profile)
        assert flag.status == EligibilityStatus.ELIGIBLE

    def test_ielts_exactly_met__eligible(self, miraz_profile):
        """User has IELTS 7.0, requirement is exactly 7.0 — met."""
        req = make_ielts_req("7.0")
        flag = _check_english(req, miraz_profile)
        assert flag.status == EligibilityStatus.ELIGIBLE

    def test_ielts_not_met__ineligible(self, miraz_profile):
        """
        FALSE POSITIVE PREVENTION.
        User has IELTS 7.0, requirement is 7.5 — not met.
        """
        req = make_ielts_req("7.5", is_strict=True)
        flag = _check_english(req, miraz_profile)
        assert flag.status == EligibilityStatus.INELIGIBLE
        assert flag.is_hard_constraint is True

    def test_ielts_close_miss__probably_eligible(self, miraz_profile):
        """User has 7.0, requirement is 7.5 but it's not explicitly strict."""
        req = make_ielts_req("7.5", is_strict=False)
        flag = _check_english(req, miraz_profile)
        assert flag.status in (
            EligibilityStatus.PROBABLY_ELIGIBLE,
            EligibilityStatus.INELIGIBLE,
        )

    def test_toefl_requirement_with_ielts_score__probably_eligible(self, miraz_profile):
        """User has IELTS, requirement is TOEFL — different test, flag as probably eligible."""
        req = ExtractedRequirement(
            requirement_type="english_toefl_min",
            value="90",
            is_strict=True,
            confidence=0.9,
            raw_text="TOEFL iBT minimum 90 required.",
        )
        flag = _check_english(req, miraz_profile)
        assert flag.status == EligibilityStatus.PROBABLY_ELIGIBLE


# ─────────────────────────────────────────────────────────────────────────────
# Deadline Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDeadline:

    def test_future_deadline__eligible(self):
        future = date.today() + timedelta(days=60)
        flag = _check_deadline(future)
        assert flag.status == EligibilityStatus.ELIGIBLE

    def test_past_deadline__ineligible(self):
        """FALSE POSITIVE PREVENTION: past deadlines must block."""
        past = date.today() - timedelta(days=1)
        flag = _check_deadline(past)
        assert flag.status == EligibilityStatus.INELIGIBLE
        assert flag.is_hard_constraint is True

    def test_no_deadline__uncertain(self):
        """No deadline found — don't assume it's fine."""
        flag = _check_deadline(None)
        assert flag.status == EligibilityStatus.UNCERTAIN

    def test_imminent_deadline__eligible_with_urgency(self):
        """Deadline in 10 days — eligible but message should mention urgency."""
        soon = date.today() + timedelta(days=10)
        flag = _check_deadline(soon)
        assert flag.status == EligibilityStatus.ELIGIBLE
        assert "10 days" in flag.message or "soon" in flag.message.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Degree Field Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDegreeField:

    def test_exact_match__eligible(self, miraz_profile):
        req = ExtractedRequirement(
            requirement_type="degree_field",
            value="Computer Science",
            is_strict=True,
            confidence=0.9,
            raw_text="Bachelor's degree in Computer Science required.",
        )
        flag = _check_degree_field(req, miraz_profile)
        assert flag.status == EligibilityStatus.ELIGIBLE

    def test_related_field__probably_eligible(self, miraz_profile):
        req = ExtractedRequirement(
            requirement_type="degree_field",
            value="Computer Science or related field",
            is_strict=None,
            confidence=0.9,
            raw_text="BSc in Computer Science or a related field.",
        )
        flag = _check_degree_field(req, miraz_profile)
        assert flag.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.PROBABLY_ELIGIBLE)

    def test_unrelated_strict_field__ineligible(self, miraz_profile):
        """FALSE POSITIVE PREVENTION: strict requirement for unrelated field."""
        req = ExtractedRequirement(
            requirement_type="degree_field",
            value="Medicine",
            is_strict=True,
            confidence=0.9,
            raw_text="Medical degree required.",
        )
        flag = _check_degree_field(req, miraz_profile)
        assert flag.status == EligibilityStatus.INELIGIBLE


# ─────────────────────────────────────────────────────────────────────────────
# Tuition Budget Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTuition:

    def test_free_tuition__eligible(self, miraz_profile):
        flag = _check_tuition(0, True, miraz_profile)
        assert flag.status == EligibilityStatus.ELIGIBLE

    def test_within_budget__eligible(self, miraz_profile):
        flag = _check_tuition(5000, False, miraz_profile)
        assert flag.status == EligibilityStatus.ELIGIBLE

    def test_over_budget_scholarship_required__uncertain(self, miraz_profile):
        """Over budget but scholarship required — uncertain (scholarship may cover it)."""
        flag = _check_tuition(15000, False, miraz_profile)
        assert flag.status == EligibilityStatus.UNCERTAIN

    def test_unknown_tuition__uncertain(self, miraz_profile):
        flag = _check_tuition(None, None, miraz_profile)
        assert flag.status == EligibilityStatus.UNCERTAIN


# ─────────────────────────────────────────────────────────────────────────────
# Full Evaluation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFullEvaluation:

    def test_perfect_match__eligible(self, miraz_profile):
        """All requirements clearly met — should be ELIGIBLE."""
        programme = make_programme(
            tuition_eur_per_year=0,
            is_tuition_free=True,
            requirements=[
                make_cgpa_req("2.5", is_strict=True),
                make_ielts_req("6.5"),
            ],
        )
        future_deadline = date.today() + timedelta(days=90)
        result = evaluate_eligibility(programme, miraz_profile, future_deadline)
        assert result.status == EligibilityStatus.ELIGIBLE

    def test_hard_cgpa_block__ineligible(self, miraz_profile):
        """
        FALSE POSITIVE PREVENTION TEST (full pipeline).
        Strict CGPA 3.0 requirement. User has 2.80. Must be INELIGIBLE.
        Even if everything else is perfect.
        """
        programme = make_programme(
            tuition_eur_per_year=0,
            is_tuition_free=True,
            requirements=[
                make_cgpa_req("3.0", is_strict=True, raw_text="Minimum GPA 3.0 required."),
                make_ielts_req("6.5"),
            ],
        )
        future_deadline = date.today() + timedelta(days=90)
        result = evaluate_eligibility(programme, miraz_profile, future_deadline)
        assert result.status == EligibilityStatus.INELIGIBLE
        assert len(result.hard_blocks) >= 1

    def test_soft_cgpa_below__probably_eligible(self, miraz_profile):
        """Soft CGPA guideline below user's score — probably eligible."""
        programme = make_programme(
            tuition_eur_per_year=0,
            is_tuition_free=True,
            requirements=[
                make_cgpa_req(
                    "3.0",
                    is_strict=False,
                    raw_text="Typically a GPA of 3.0 is expected.",
                ),
                make_ielts_req("6.5"),
            ],
        )
        future_deadline = date.today() + timedelta(days=90)
        result = evaluate_eligibility(programme, miraz_profile, future_deadline)
        assert result.status in (
            EligibilityStatus.PROBABLY_ELIGIBLE,
            EligibilityStatus.UNCERTAIN,
        )

    def test_passed_deadline__ineligible(self, miraz_profile):
        """Passed deadline overrides everything."""
        programme = make_programme(requirements=[make_ielts_req("6.5")])
        past_deadline = date.today() - timedelta(days=5)
        result = evaluate_eligibility(programme, miraz_profile, past_deadline)
        assert result.status == EligibilityStatus.INELIGIBLE

    def test_no_requirements__uncertain(self, miraz_profile):
        """Programme with no extractable requirements — uncertain."""
        programme = make_programme(requirements=[])
        future = date.today() + timedelta(days=90)
        result = evaluate_eligibility(programme, miraz_profile, future)
        assert result.status == EligibilityStatus.UNCERTAIN

    def test_result_has_summary(self, miraz_profile):
        """Every result must have a non-empty summary."""
        programme = make_programme(requirements=[make_ielts_req("6.5")])
        future = date.today() + timedelta(days=90)
        result = evaluate_eligibility(programme, miraz_profile, future)
        assert result.summary
        assert len(result.summary) > 20


# ─────────────────────────────────────────────────────────────────────────────
# Date Parser Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDateParser:

    def test_iso_format(self):
        assert parse_date_safe("2025-12-01") == date(2025, 12, 1)

    def test_natural_language(self):
        result = parse_date_safe("1 December 2025")
        assert result == date(2025, 12, 1)

    def test_us_format(self):
        result = parse_date_safe("December 1, 2025")
        assert result == date(2025, 12, 1)

    def test_none_input(self):
        assert parse_date_safe(None) is None

    def test_empty_string(self):
        assert parse_date_safe("") is None

    def test_unparseable(self):
        assert parse_date_safe("early next year") is None

    def test_days_until_future(self):
        future = date.today() + timedelta(days=30)
        assert days_until(future) == 30

    def test_days_until_past(self):
        past = date.today() - timedelta(days=5)
        assert days_until(past) == -5

    def test_is_upcoming_true(self):
        soon = date.today() + timedelta(days=15)
        assert is_upcoming(soon, within_days=30) is True

    def test_is_upcoming_false(self):
        far = date.today() + timedelta(days=60)
        assert is_upcoming(far, within_days=30) is False

    def test_is_passed_true(self):
        past = date.today() - timedelta(days=1)
        assert is_passed(past) is True

    def test_is_passed_false(self):
        future = date.today() + timedelta(days=1)
        assert is_passed(future) is False
