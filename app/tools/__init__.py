"""
app/tools/__init__.py
─────────────────────
Tool exports.

Tools are thin, testable wrappers over external APIs.
Agents call tools. Tools never call agents.
"""

from app.tools.base import (
    PageContent,
    PDFContent,
    SearchResponse,
    SearchResult,
    ToolError,
    ToolErrorType,
)
from app.tools.page_fetch import fetch_page, fetch_page_rendered, fetch_pdf
from app.tools.web_search import search_web

__all__ = [
    # Types
    "SearchResult",
    "SearchResponse",
    "PageContent",
    "PDFContent",
    "ToolError",
    "ToolErrorType",
    # Functions
    "search_web",
    "fetch_page",
    "fetch_page_rendered",
    "fetch_pdf",
]
