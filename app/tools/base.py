"""
app/tools/base.py
─────────────────
Base types and exceptions shared by all tools.

Why define custom exceptions?
Because "an error occurred" is useless. A typed exception tells you:
- WHAT went wrong (rate limit vs network vs parse error)
- WHERE it went wrong (which tool, which URL)
- WHETHER to retry (rate limits: yes. Parse errors: no point)

This is one of the most important habits in production engineering:
fail loudly, fail specifically, never silently swallow errors.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ToolErrorType(str, Enum):
    RATE_LIMITED = "rate_limited"        # API quota hit — back off and retry later
    NETWORK_ERROR = "network_error"      # Timeout, DNS failure, connection reset
    NOT_FOUND = "not_found"              # 404 — page doesn't exist
    ACCESS_DENIED = "access_denied"      # 403/401 — blocked or auth required
    PARSE_ERROR = "parse_error"          # Page fetched but content can't be parsed
    INVALID_INPUT = "invalid_input"      # Bad URL, missing parameter
    EXTERNAL_API_ERROR = "external_api_error"  # API returned unexpected response
    UNKNOWN = "unknown"


class ToolError(Exception):
    """
    Base exception for all tool failures.
    Always carries the error type, message, and optional context.
    """
    def __init__(
        self,
        error_type: ToolErrorType,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.url = url
        self.status_code = status_code
        self.retryable = retryable  # should the caller retry this?

    def __repr__(self) -> str:
        return (
            f"ToolError(type={self.error_type}, "
            f"message={self.message!r}, "
            f"url={self.url!r}, "
            f"retryable={self.retryable})"
        )


@dataclass
class SearchResult:
    """A single result from a web search."""
    title: str
    url: str
    snippet: str
    score: float = 0.0          # relevance score from search API (0-1)
    published_date: str | None = None


@dataclass
class SearchResponse:
    """The full response from a web search query."""
    query: str
    results: list[SearchResult]
    total_results: int
    search_time_ms: float = 0.0


@dataclass
class PageContent:
    """
    The content retrieved from a single web page.

    We store both raw HTML and cleaned markdown because:
    - Raw HTML is needed for re-parsing if our initial parse was wrong
    - Cleaned markdown is what we send to the LLM (much smaller, cheaper)
    """
    url: str
    title: str | None
    markdown: str           # cleaned text ready for LLM
    raw_html: str | None    # original HTML (kept for debugging/re-parsing)
    status_code: int
    content_type: str | None
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    word_count: int = 0
    is_pdf: bool = False


@dataclass
class PDFContent:
    """Text extracted from a PDF document."""
    url: str
    title: str | None
    text: str               # full extracted text
    page_count: int
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    word_count: int = 0
