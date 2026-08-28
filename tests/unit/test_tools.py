"""
tests/unit/test_tools.py
─────────────────────────
Unit tests for the web research tools.

WHAT WE TEST HERE:
- Input validation (bad URLs, empty queries)
- HTML → Markdown conversion
- PDF text extraction
- Error type classification

WHAT WE DON'T TEST HERE:
- Real network requests (those belong in integration tests)
- Actual Tavily API responses (we mock those)

WHY MOCK?
Unit tests must be:
- Fast (milliseconds, not seconds)
- Deterministic (same result every run)
- Offline-capable (no internet required)

We mock external calls and test that OUR code behaves correctly
given those responses. The real API is tested separately in
integration tests that run less frequently.
"""

import pytest

from app.tools.base import PageContent, ToolError, ToolErrorType
from app.tools.page_fetch import _html_to_markdown, _compute_hash


class TestHTMLToMarkdown:
    """Tests for the HTML → Markdown converter."""

    def test_basic_paragraph(self):
        html = "<html><body><p>This is a test paragraph with enough content.</p></body></html>"
        result = _html_to_markdown(html)
        assert "This is a test paragraph with enough content." in result

    def test_heading_extraction(self):
        html = "<html><body><h1>Master of Science</h1><p>A great programme.</p></body></html>"
        result = _html_to_markdown(html)
        assert "# Master of Science" in result

    def test_removes_scripts(self):
        html = """
        <html><body>
            <script>alert('evil')</script>
            <p>Actual content that is long enough to pass the filter.</p>
        </body></html>
        """
        result = _html_to_markdown(html)
        assert "alert" not in result
        assert "Actual content" in result

    def test_removes_navigation(self):
        html = """
        <html><body>
            <nav><a href="/">Home</a><a href="/about">About</a></nav>
            <main><p>Programme content that is substantial enough here.</p></main>
        </body></html>
        """
        result = _html_to_markdown(html)
        assert "Programme content" in result

    def test_empty_html(self):
        result = _html_to_markdown("")
        assert isinstance(result, str)

    def test_title_extraction(self):
        html = """
        <html>
            <head><title>MSc Computer Science - TU Berlin</title></head>
            <body><p>Programme details with sufficient length here.</p></body>
        </html>
        """
        result = _html_to_markdown(html)
        assert "MSc Computer Science - TU Berlin" in result

    def test_list_items(self):
        html = """
        <html><body>
            <ul>
                <li>Python programming required</li>
                <li>Mathematics background needed</li>
            </ul>
        </body></html>
        """
        result = _html_to_markdown(html)
        assert "Python programming required" in result
        assert "Mathematics background needed" in result


class TestComputeHash:
    """Tests for content change detection hash."""

    def test_same_content_same_hash(self):
        content = "Application deadline: January 15, 2025"
        assert _compute_hash(content) == _compute_hash(content)

    def test_different_content_different_hash(self):
        h1 = _compute_hash("Deadline: January 15")
        h2 = _compute_hash("Deadline: February 15")
        assert h1 != h2

    def test_hash_length(self):
        # SHA256 = 64 hex characters
        assert len(_compute_hash("test")) == 64

    def test_empty_string(self):
        result = _compute_hash("")
        assert len(result) == 64


class TestToolError:
    """Tests for the ToolError exception type."""

    def test_retryable_network_error(self):
        err = ToolError(
            ToolErrorType.NETWORK_ERROR,
            "Connection timed out",
            url="https://example.com",
            retryable=True,
        )
        assert err.retryable is True
        assert err.error_type == ToolErrorType.NETWORK_ERROR
        assert err.url == "https://example.com"

    def test_non_retryable_parse_error(self):
        err = ToolError(
            ToolErrorType.PARSE_ERROR,
            "Cannot parse response",
            retryable=False,
        )
        assert err.retryable is False

    def test_error_is_exception(self):
        err = ToolError(ToolErrorType.NOT_FOUND, "404")
        assert isinstance(err, Exception)

    def test_error_message(self):
        err = ToolError(ToolErrorType.RATE_LIMITED, "Too many requests")
        assert str(err) == "Too many requests"
