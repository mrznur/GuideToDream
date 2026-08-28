"""
tests/unit/test_scoring.py
───────────────────────────
Tests for the scoring engine.

We test:
1. Each dimension scoring function independently
2. Full score calculation
3. Eligibility modifier (UNCERTAIN/PROBABLY caps the score)
4. Ineligible programmes get score 0
5. Score explanation is present and non-empty
6. Score label boundaries
"""

from datetime import date, timedelta

import pytest

from app.agents.extraction_agent import ExtractedProgramme, ExtractedRequirement
from app.services.eligibility_service import (
    EligibilityFlag,
    EligibilityResult,
    EligibilityStatus,
    UserProfileSnapshot,
)
from app.services.scoring_service import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    ScoreResult,
    _score_academic_fit,
    _score_country,
    _score_deadline_urgency,
    _score_financial_fit,
    _score_label,
    _score_portfolio_fit,
    _score_reputation,
    _score_scholarship,
    score_opportunity,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def profile() -> UserProfileSnapshot:
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
        preferred_countries=["Germany", "Netherlands", "Czech Republic"],
        avoided_countries=["France"],
        graduation_year=2026,
        graduation_month=5,
        skills={
            "python": "advanced",
            "pytorch": "intermediate",
            "transformers": "intermediate",
            "fastapi": "advanced",
            "prompt_engineering": "advanced",
        },
        notable_projects=[
            {"name": "Thesis: Tree of Thoughts"},
            {"name": "Face Detection System"},
        ],
    )


@pytest.fixture
def eligible_result() -> EligibilityResult:
    return EligibilityResult(
        status=EligibilityStatus.ELIGIBLE,
        flags=[],
        summary="All requirements met.",
    )


@pytest.fixture
def uncertain_result() -> EligibilityResult:
    return EligibilityResult(
        status=EligibilityStatus.UNCERTAIN,
        flags=[
            EligibilityFlag(
                check="cgpa_minimum",
                status=EligibilityStatus.UNCERTAIN,
                message="CGPA requirement ambiguous",
                is_hard_constraint=False,
            )
        ],
        summary="Uncertain",
    )


@pytest.fixture
def ineligible_result() -> EligibilityResult:
    return EligibilityResult(
        status=EligibilityStatus.INELIGIBLE,
        flags=[
            EligibilityFlag(
                check="cgpa_minimum",
                status=EligibilityStatus.INELIGIBLE,
                message="Hard CGPA cutoff not met",
                is_hard_constraint=True,
            )
        ],
        summary="Ineligible",
    )


def make_programme(**kwargs) -> ExtractedProgramme:
    defaults = {
        "programme_name": "MSc Computer Science",
        "university_name": "TU Berlin",
        "degree_type": "MSc",
        "field": "Computer Science",
        "language_of_instruction": "English",
        "confidence_overall": 0.9,
    }
    defaults.update(kwargs)
    return ExtractedProgramme(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# Dimension weight validation
# ─────────────────────────────────────────────────────────────────────────────

class TestWeights:
    def test_weights_sum_to_one(self):
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_weights_positive(self):
        for name, weight in DIMENSION_WEIGHTS.items():
            assert weight > 0, f"Weight for {name} must be positive"


# ─────────────────────────────────────────────────────────────────────────────
# Academic Fit
# ─────────────────────────────────────────────────────────────────────────────

class TestAcademicFit:

    def test_exact_cs_match_in_interests(self, profile):
        prog = make_programme(field="Computer Science")
        result = _score_academic_fit(prog, profile)
        assert result.score >= 0.8

    def test_ai_programme_in_interests(self, profile):
        prog = make_programme(field="Artificial Intelligence")
        result = _score_academic_fit(prog, profile)
        assert result.score >= 0.5

    def test_unrelated_field_low_score(self, profile):
        prog = make_programme(field="History")
        result = _score_academic_fit(prog, profile)
        assert result.score <= 0.3

    def test_no_field_gives_partial_score(self, profile):
        prog = make_programme(field=None)
        result = _score_academic_fit(prog, profile)
        assert 0.2 <= result.score <= 0.6

    def test_reason_is_non_empty(self, profile):
        prog = make_programme(field="Computer Science")
        result = _score_academic_fit(prog, profile)
        assert len(result.reason) > 10


# ─────────────────────────────────────────────────────────────────────────────
# Financial Fit
# ─────────────────────────────────────────────────────────────────────────────

class TestFinancialFit:

    def test_free_tuition_perfect_score(self, profile):
        prog = make_programme(tuition_eur_per_year=0, is_tuition_free=True)
        result = _score_financial_fit(prog, profile)
        assert result.score == 1.0

    def test_admin_fee_only_near_perfect(self, profile):
        prog = make_programme(tuition_eur_per_year=400, is_tuition_free=False)
        result = _score_financial_fit(prog, profile)
        assert result.score >= 0.85

    def test_within_budget_good_score(self, profile):
        prog = make_programme(tuition_eur_per_year=5000)
        result = _score_financial_fit(prog, profile)
        assert result.score >= 0.5

    def test_over_budget_low_score(self, profile):
        prog = make_programme(tuition_eur_per_year=20000)
        result = _score_financial_fit(prog, profile)
        assert result.score <= 0.3

    def test_unknown_tuition_partial_score(self, profile):
        prog = make_programme(tuition_eur_per_year=None)
        result = _score_financial_fit(prog, profile)
        assert 0.2 <= result.score <= 0.6


# ─────────────────────────────────────────────────────────────────────────────
# Scholarship
# ─────────────────────────────────────────────────────────────────────────────

class TestScholarship:

    def test_full_scholarship_max_score(self, profile):
        result = _score_scholarship(True, "full", profile)
        assert result.score == 1.0

    def test_tuition_waiver_high_score(self, profile):
        result = _score_scholarship(True, "tuition_waiver", profile)
        assert result.score >= 0.7

    def test_no_scholarship_when_required_low_score(self, profile):
        result = _score_scholarship(False, None, profile)
        assert result.score <= 0.2

    def test_partial_scholarship_mid_score(self, profile):
        result = _score_scholarship(True, "partial", profile)
        assert 0.4 <= result.score <= 0.8


# ─────────────────────────────────────────────────────────────────────────────
# Country Preference
# ─────────────────────────────────────────────────────────────────────────────

class TestCountryPreference:

    def test_preferred_country_max_score(self, profile):
        prog = make_programme(university_name="TU Berlin, Germany")
        result = _score_country(prog, profile)
        assert result.score == 1.0

    def test_avoided_country_zero_score(self, profile):
        prog = make_programme(university_name="University of Paris, France")
        result = _score_country(prog, profile)
        assert result.score == 0.0

    def test_neutral_country_mid_score(self, profile):
        prog = make_programme(university_name="University of Zurich, Switzerland")
        result = _score_country(prog, profile)
        assert result.score == 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Deadline Urgency
# ─────────────────────────────────────────────────────────────────────────────

class TestDeadlineUrgency:

    def test_urgent_deadline_high_score(self):
        soon = date.today() + timedelta(days=15)
        result = _score_deadline_urgency(soon)
        assert result.score == 1.0
        assert "URGENT" in result.reason.upper() or "urgent" in result.reason.lower()

    def test_far_deadline_low_urgency(self):
        far = date.today() + timedelta(days=200)
        result = _score_deadline_urgency(far)
        assert result.score <= 0.3

    def test_no_deadline_partial_score(self):
        result = _score_deadline_urgency(None)
        assert 0.1 <= result.score <= 0.5

    def test_past_deadline_zero_score(self):
        past = date.today() - timedelta(days=5)
        result = _score_deadline_urgency(past)
        assert result.score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Reputation
# ─────────────────────────────────────────────────────────────────────────────

class TestReputation:

    def test_top_100_perfect_score(self):
        result = _score_reputation(50)
        assert result.score == 1.0

    def test_top_200_high_score(self):
        result = _score_reputation(150)
        assert result.score >= 0.75

    def test_unranked_partial_score(self):
        result = _score_reputation(None)
        assert 0.3 <= result.score <= 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Score Label
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreLabel:

    def test_exceptional_label(self):
        assert _score_label(95) == "Exceptional match"

    def test_strong_label(self):
        assert _score_label(80) == "Strong match"

    def test_good_label(self):
        assert _score_label(65) == "Good match"

    def test_moderate_label(self):
        assert _score_label(50) == "Moderate match"

    def test_weak_label(self):
        assert _score_label(30) == "Weak match"


# ─────────────────────────────────────────────────────────────────────────────
# Full Score Calculation
# ─────────────────────────────────────────────────────────────────────────────

class TestFullScoring:

    def test_ineligible_gets_zero(self, profile, ineligible_result):
        prog = make_programme()
        result = score_opportunity(prog, profile, ineligible_result)
        assert result.total_score == 0.0
        assert result.score_label == "Ineligible"

    def test_score_is_0_to_100(self, profile, eligible_result):
        prog = make_programme(
            tuition_eur_per_year=0,
            is_tuition_free=True,
            field="Computer Science",
        )
        future = date.today() + timedelta(days=90)
        result = score_opportunity(
            prog, profile, eligible_result,
            application_deadline=future,
            has_scholarship=True,
            scholarship_coverage_type="full",
        )
        assert 0 <= result.total_score <= 100

    def test_uncertain_eligibility_caps_score(self, profile, uncertain_result):
        """UNCERTAIN eligibility must cap total score at 72."""
        prog = make_programme(
            tuition_eur_per_year=0,
            is_tuition_free=True,
            field="Computer Science",
        )
        future = date.today() + timedelta(days=90)
        result = score_opportunity(
            prog, profile, uncertain_result,
            application_deadline=future,
            has_scholarship=True,
            scholarship_coverage_type="full",
        )
        assert result.total_score <= 72.0

    def test_explanation_is_non_empty(self, profile, eligible_result):
        prog = make_programme()
        result = score_opportunity(prog, profile, eligible_result)
        assert result.explanation
        assert len(result.explanation) > 50

    def test_breakdown_dict_has_all_dimensions(self, profile, eligible_result):
        prog = make_programme()
        result = score_opportunity(prog, profile, eligible_result)
        breakdown = result.breakdown_dict
        for dim in DIMENSION_WEIGHTS.keys():
            assert dim in breakdown, f"Missing dimension: {dim}"

    def test_free_tuition_full_scholarship_cs_germany_high_score(self, profile, eligible_result):
        """
        A free programme in Germany with full scholarship in CS
        should score highly for this profile.
        """
        prog = make_programme(
            programme_name="MSc Computer Science",
            university_name="Technical University of Munich, Germany",
            field="Computer Science",
            tuition_eur_per_year=0,
            is_tuition_free=True,
            language_of_instruction="English",
        )
        future = date.today() + timedelta(days=90)
        result = score_opportunity(
            prog, profile, eligible_result,
            application_deadline=future,
            has_scholarship=True,
            scholarship_coverage_type="full",
            qs_rank=50,
        )
        assert result.total_score >= 80, (
            f"Expected score >= 80 for ideal opportunity, got {result.total_score}\n"
            f"{result.explanation}"
        )

    def test_score_result_ineligible_class_method(self):
        result = ScoreResult.ineligible("Hard CGPA cutoff not met")
        assert result.total_score == 0.0
        assert "ineligible" in result.explanation.lower()
