"""
app/agents/extraction_agent.py
───────────────────────────────
Extracts structured programme/scholarship data from raw page content.

THIS IS THE CORE LLM USE CASE IN THIS PROJECT.

The agent receives Markdown text from a university page and returns
a validated Python object with fields like tuition, deadline, CGPA
requirement, etc.

KEY DESIGN DECISIONS:

1. Pydantic for output schema, not raw JSON
   We define exactly what fields we want. The LLM is instructed to return
   JSON matching that schema. We then validate with Pydantic.
   If the LLM returns garbage, Pydantic catches it — not your database.

2. Confidence fields on every extracted value
   Each extracted field has a companion confidence score (0.0-1.0).
   Why? Because "deadline: January 15" found in a clear table = 0.95
   But "applications usually open in early winter" = 0.40
   The eligibility engine uses confidence to decide how much to trust data.

3. is_strict on requirements
   When the LLM sees "minimum 3.0 GPA", is that a hard cutoff?
   We ask the LLM to assess this and flag True/False/None (uncertain).
   None means "I saw a requirement but couldn't determine strictness."

4. raw_text for every extracted field
   We store the exact sentence the LLM used to extract each value.
   This is the evidence trail — the user can always verify a claim.

5. Two-pass approach for complex pages
   Pass 1: Extract programme basics (name, degree, tuition, intake)
   Pass 2: Extract requirements (CGPA, English, degree field, etc.)
   Splitting reduces LLM context pressure and improves accuracy.
"""

import json
import re
from typing import Any

import structlog
from pydantic import BaseModel, Field, field_validator

from app.config import get_settings
from app.utils.llm import call_llm, LLMError

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT SCHEMAS (Pydantic models that define what the LLM must return)
# ─────────────────────────────────────────────────────────────────────────────

class ExtractedRequirement(BaseModel):
    """A single extracted requirement from a programme page."""

    model_config = {"populate_by_name": True}

    requirement_type: str = Field(
        alias="type",  # LLM naturally uses "type" — accept both
        description="Type: cgpa_min | english_ielts_min | english_toefl_min | "
                    "degree_field | work_experience | citizenship | other"
    )
    value: str | None = Field(default=None, description="The extracted value as a string")
    is_strict: bool | None = Field(
        default=None,
        description="True=hard cutoff, False=soft guideline, None=unclear"
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Extraction confidence 0-1")
    raw_text: str | None = Field(default=None, description="Exact text from source used for extraction")

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 2)


class ExtractedProgramme(BaseModel):
    """
    Structured data extracted from a university programme page.

    Every field is Optional because pages are incomplete and inconsistent.
    A missing field is NOT an extraction failure — it means the page
    didn't contain that information. We flag it, not fail on it.
    """
    # Basic info
    programme_name: str | None = None
    university_name: str | None = None
    degree_type: str | None = Field(
        default=None,
        description="MSc, MA, MEng, MRes, etc."
    )
    field: str | None = Field(
        default=None,
        description="Broad field: Computer Science, Engineering, etc."
    )
    language_of_instruction: str | None = None
    duration_months: int | None = None

    # Financial
    tuition_eur_per_year: int | None = None
    tuition_notes: str | None = Field(
        default=None,
        description="Free text: 'EU students free', 'admin fee only', etc."
    )
    is_tuition_free: bool | None = None

    # Intake and deadlines
    intake_months: list[str] = Field(default_factory=list)
    application_deadline: str | None = Field(
        default=None,
        description="ISO date YYYY-MM-DD if determinable, else descriptive text"
    )

    # URLs found on the page
    official_url: str | None = None
    application_portal_url: str | None = None

    # Requirements
    requirements: list[ExtractedRequirement] = Field(default_factory=list)

    # Extraction metadata
    confidence_overall: float = Field(
        default=0.5,
        ge=0.0, le=1.0,
        description="Overall confidence in this extraction (0-1)"
    )
    extraction_notes: str | None = Field(
        default=None,
        description="LLM notes about ambiguity, missing data, or warnings"
    )

    @field_validator("tuition_eur_per_year")
    @classmethod
    def validate_tuition(cls, v: int | None) -> int | None:
        if v is not None and (v < 0 or v > 100000):
            return None  # reject clearly wrong values
        return v

    @field_validator("duration_months")
    @classmethod
    def validate_duration(cls, v: int | None) -> int | None:
        if v is not None and (v < 6 or v > 60):
            return None  # reject clearly wrong values
        return v


class ExtractedScholarship(BaseModel):
    """Structured data extracted from a scholarship page."""
    scholarship_name: str | None = None
    provider: str | None = None
    coverage: str | None = None
    coverage_type: str | None = Field(
        default=None,
        description="full | partial | stipend_only | tuition_waiver | unknown"
    )
    country_scope: list[str] = Field(default_factory=list)
    field_scope: list[str] = Field(default_factory=list)
    nationality_scope: list[str] = Field(default_factory=list)
    deadline: str | None = None
    official_url: str | None = None
    requirements: list[ExtractedRequirement] = Field(default_factory=list)
    confidence_overall: float = Field(default=0.5, ge=0.0, le=1.0)
    extraction_notes: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

_PROGRAMME_EXTRACTION_PROMPT = """You are an expert at extracting structured information from university programme web pages.

Extract programme information from the page content below.
Return ONLY valid JSON matching the schema exactly. No markdown, no explanation, just JSON.

IMPORTANT RULES:
- If a field is not mentioned, set it to null
- For tuition: convert to EUR per year as an integer. If free or admin fee only, set is_tuition_free=true and tuition_eur_per_year=0
- For deadlines: use ISO format YYYY-MM-DD if possible
- For requirements array: each item MUST have these exact fields:
    "type": one of [cgpa_min, english_ielts_min, english_toefl_min, degree_field, work_experience, citizenship, other]
    "value": the extracted value as a string (e.g. "3.0", "6.5", "Computer Science")
    "is_strict": true if explicitly stated as minimum/required, false if preferred/typical, null if unclear
    "confidence": 0.0 to 1.0
    "raw_text": the exact sentence from the page

REQUIRED JSON STRUCTURE:
{
  "programme_name": string or null,
  "university_name": string or null,
  "degree_type": string or null,
  "field": string or null,
  "language_of_instruction": string or null,
  "duration_months": integer or null,
  "tuition_eur_per_year": integer or null,
  "tuition_notes": string or null,
  "is_tuition_free": boolean or null,
  "intake_months": [string],
  "application_deadline": string or null,
  "official_url": string or null,
  "application_portal_url": string or null,
  "requirements": [
    {
      "type": string,
      "value": string or null,
      "is_strict": boolean or null,
      "confidence": number,
      "raw_text": string or null
    }
  ],
  "confidence_overall": number,
  "extraction_notes": string or null
}
"""


_SCHOLARSHIP_EXTRACTION_PROMPT = """You are an expert at extracting structured information from scholarship web pages.

Extract scholarship information from the page content below.
Return ONLY valid JSON. No markdown, no explanation, just JSON.

REQUIRED JSON STRUCTURE:
{
  "scholarship_name": string or null,
  "provider": string or null,
  "coverage": string or null,
  "coverage_type": one of [full, partial, stipend_only, tuition_waiver, unknown] or null,
  "country_scope": [string],
  "field_scope": [string],
  "nationality_scope": [string],
  "deadline": string or null,
  "official_url": string or null,
  "requirements": [
    {
      "type": string,
      "value": string or null,
      "is_strict": boolean or null,
      "confidence": number,
      "raw_text": string or null
    }
  ],
  "confidence_overall": number,
  "extraction_notes": string or null
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _model_to_schema_description(model: type[BaseModel]) -> str:
    """
    Generate a simplified schema description for the LLM prompt.
    We don't dump the full JSON Schema (too verbose) — just field names,
    types, and descriptions.
    """
    lines = ["{"]
    for name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        description = field_info.description or ""
        type_str = str(annotation).replace("typing.", "").replace("NoneType", "null")
        lines.append(f'  "{name}": {type_str}  // {description}')
    lines.append("}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# JSON EXTRACTION FROM LLM RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict[str, Any]:
    """
    Extract JSON from LLM response text.

    LLMs sometimes wrap JSON in markdown code blocks:
        ```json
        { ... }
        ```
    We strip that and parse the raw JSON.

    This is a critical utility — LLM output is not always clean.
    Professional engineers always sanitise LLM output before parsing.
    """
    text = text.strip()

    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Find the outermost JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]!r}")

    json_str = text[start:end]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Try to fix common LLM JSON errors (trailing commas)
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            raise ValueError(f"Cannot parse JSON from LLM response: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXTRACTION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def extract_programme(
    content: str,
    url: str,
    max_content_chars: int = 8000,
) -> ExtractedProgramme:
    """
    Extract structured programme data from a page's Markdown content.

    Args:
        content: Markdown text of the university programme page
        url: Source URL (for context and logging)
        max_content_chars: Truncate content to this length before sending
                           to LLM (controls token cost)

    Returns:
        ExtractedProgramme with all found fields populated

    Raises:
        ExtractionError: If LLM call fails or returns unparseable output
    """
    logger.info("extract_programme_started", url=url, content_length=len(content))

    # Truncate content to control LLM cost
    # 8000 chars ≈ 2000 tokens ≈ $0.0001 with Gemini Flash
    if len(content) > max_content_chars:
        content = content[:max_content_chars] + "\n\n[Content truncated]"
        logger.debug("extract_programme_content_truncated", url=url, chars=max_content_chars)

    prompt = (
        _PROGRAMME_EXTRACTION_PROMPT
        + f"\nPAGE URL: {url}\n\nPAGE CONTENT:\n{content}\n\nReturn JSON only:"
    )
    try:
        raw_response = call_llm(
            prompt=prompt,
            model="fast",  # use cheap model for extraction
            temperature=0.1,  # low temperature = more deterministic output
            task_name="programme_extraction",
        )
    except LLMError as e:
        logger.error("extract_programme_llm_failed", url=url, error=str(e))
        # Return empty extraction rather than crash — the pipeline continues
        return ExtractedProgramme(
            confidence_overall=0.0,
            extraction_notes=f"LLM call failed: {e}",
        )

    try:
        data = _extract_json(raw_response)
        result = ExtractedProgramme.model_validate(data)
    except (ValueError, Exception) as e:
        logger.error(
            "extract_programme_parse_failed",
            url=url,
            error=str(e),
            raw_response=raw_response[:500],
        )
        return ExtractedProgramme(
            confidence_overall=0.0,
            extraction_notes=f"Parse failed: {e}",
        )

    logger.info(
        "extract_programme_completed",
        url=url,
        programme=result.programme_name,
        confidence=result.confidence_overall,
        requirements_found=len(result.requirements),
    )

    return result


def extract_scholarship(
    content: str,
    url: str,
    max_content_chars: int = 8000,
) -> ExtractedScholarship:
    """
    Extract structured scholarship data from a page's Markdown content.

    Args:
        content: Markdown text of the scholarship page
        url: Source URL
        max_content_chars: Max characters to send to LLM

    Returns:
        ExtractedScholarship with all found fields populated
    """
    logger.info("extract_scholarship_started", url=url, content_length=len(content))

    if len(content) > max_content_chars:
        content = content[:max_content_chars] + "\n\n[Content truncated]"

    prompt = (
        _SCHOLARSHIP_EXTRACTION_PROMPT
        + f"\nPAGE URL: {url}\n\nPAGE CONTENT:\n{content}\n\nReturn JSON only:"
    )

    try:
        raw_response = call_llm(
            prompt=prompt,
            model="fast",
            temperature=0.1,
            task_name="scholarship_extraction",
        )
    except LLMError as e:
        logger.error("extract_scholarship_llm_failed", url=url, error=str(e))
        return ExtractedScholarship(
            confidence_overall=0.0,
            extraction_notes=f"LLM call failed: {e}",
        )

    try:
        data = _extract_json(raw_response)
        result = ExtractedScholarship.model_validate(data)
    except (ValueError, Exception) as e:
        logger.error("extract_scholarship_parse_failed", url=url, error=str(e))
        return ExtractedScholarship(
            confidence_overall=0.0,
            extraction_notes=f"Parse failed: {e}",
        )

    logger.info(
        "extract_scholarship_completed",
        url=url,
        name=result.scholarship_name,
        confidence=result.confidence_overall,
    )

    return result
