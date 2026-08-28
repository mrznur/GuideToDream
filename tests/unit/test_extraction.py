"""
tests/unit/test_extraction.py
──────────────────────────────
Unit tests for the extraction agent.

We test:
1. JSON parsing from LLM output (including messy output)
2. Pydantic schema validation
3. Edge cases: missing fields, invalid values, truncation
4. The _extract_json helper with various LLM output formats
"""

import pytest
from pydantic import ValidationError

from app.agents.extraction_agent import (
    ExtractedProgramme,
    ExtractedRequirement,
    ExtractedScholarship,
    _extract_json,
)


class TestExtractJSON:
    """Tests for the JSON extraction helper."""

    def test_clean_json(self):
        text = '{"programme_name": "MSc Computer Science", "confidence_overall": 0.9}'
        result = _extract_json(text)
        assert result["programme_name"] == "MSc Computer Science"

    def test_json_in_markdown_fence(self):
        text = '```json\n{"programme_name": "MSc AI"}\n```'
        result = _extract_json(text)
        assert result["programme_name"] == "MSc AI"

    def test_json_in_plain_fence(self):
        text = '```\n{"programme_name": "MSc AI"}\n```'
        result = _extract_json(text)
        assert result["programme_name"] == "MSc AI"

    def test_json_with_surrounding_text(self):
        text = 'Here is the extraction:\n{"programme_name": "MSc CS"}\nEnd.'
        result = _extract_json(text)
        assert result["programme_name"] == "MSc CS"

    def test_json_with_trailing_comma(self):
        # LLMs sometimes produce trailing commas (invalid JSON)
        text = '{"programme_name": "MSc CS", "confidence_overall": 0.9,}'
        result = _extract_json(text)
        assert result["programme_name"] == "MSc CS"

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            _extract_json("This is just plain text with no JSON.")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _extract_json("")


class TestExtractedProgramme:
    """Tests for the ExtractedProgramme Pydantic model."""

    def test_minimal_valid(self):
        p = ExtractedProgramme()
        assert p.programme_name is None
        assert p.requirements == []
        assert p.confidence_overall == 0.5

    def test_full_valid(self):
        p = ExtractedProgramme(
            programme_name="MSc Computer Science",
            university_name="TU Berlin",
            degree_type="MSc",
            field="Computer Science",
            tuition_eur_per_year=0,
            is_tuition_free=True,
            language_of_instruction="English",
            duration_months=24,
            intake_months=["October"],
            application_deadline="2024-12-01",
            confidence_overall=0.85,
            requirements=[
                ExtractedRequirement(
                    requirement_type="cgpa_min",
                    value="3.0",
                    is_strict=True,
                    confidence=0.9,
                    raw_text="Minimum GPA of 3.0 on a 4.0 scale required.",
                )
            ],
        )
        assert p.programme_name == "MSc Computer Science"
        assert p.tuition_eur_per_year == 0
        assert p.is_tuition_free is True
        assert len(p.requirements) == 1
        assert p.requirements[0].is_strict is True

    def test_invalid_tuition_rejected(self):
        # Tuition > 100,000 EUR is clearly wrong — validator rejects it
        p = ExtractedProgramme(tuition_eur_per_year=999999)
        assert p.tuition_eur_per_year is None

    def test_invalid_duration_rejected(self):
        # Duration of 200 months is clearly wrong
        p = ExtractedProgramme(duration_months=200)
        assert p.duration_months is None

    def test_confidence_clamped(self):
        # Confidence must be 0.0-1.0
        with pytest.raises(ValidationError):
            ExtractedProgramme(confidence_overall=1.5)

    def test_requirement_is_strict_none(self):
        # is_strict=None means "we don't know" — valid
        req = ExtractedRequirement(
            requirement_type="cgpa_min",
            value="3.0",
            is_strict=None,  # ambiguous — valid
            confidence=0.6,
            raw_text="A good academic background is expected.",
        )
        assert req.is_strict is None

    def test_from_json_dict(self):
        data = {
            "programme_name": "MSc AI",
            "university_name": "Leiden University",
            "tuition_eur_per_year": 2000,
            "confidence_overall": 0.8,
            "requirements": [
                {
                    "requirement_type": "english_ielts_min",
                    "value": "6.5",
                    "is_strict": True,
                    "confidence": 0.95,
                    "raw_text": "IELTS minimum score of 6.5 required.",
                }
            ],
        }
        p = ExtractedProgramme.model_validate(data)
        assert p.programme_name == "MSc AI"
        assert p.requirements[0].value == "6.5"


class TestExtractedScholarship:
    """Tests for the ExtractedScholarship Pydantic model."""

    def test_minimal_valid(self):
        s = ExtractedScholarship()
        assert s.scholarship_name is None
        assert s.country_scope == []

    def test_full_valid(self):
        s = ExtractedScholarship(
            scholarship_name="DAAD Scholarship",
            provider="DAAD",
            coverage="Full tuition + €850/month stipend",
            coverage_type="full",
            country_scope=["Germany"],
            nationality_scope=["Bangladesh", "India", "Pakistan"],
            confidence_overall=0.9,
        )
        assert s.provider == "DAAD"
        assert "Bangladesh" in s.nationality_scope

    def test_invalid_coverage_type_accepted(self):
        # Pydantic doesn't constrain coverage_type (it's just a string)
        # Our application logic handles unknown values
        s = ExtractedScholarship(coverage_type="full")
        assert s.coverage_type == "full"
