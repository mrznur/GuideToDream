"""
app/tools/page_fetch.py
────────────────────────
Fetches web pages and converts them to clean Markdown for LLM processing.

TWO FETCH MODES:

1. Static fetch (httpx) — fast, cheap, default
   Use for: university pages, most programme pages
   Can't handle: pages that load content via JavaScript after page load

2. Rendered fetch (Playwright) — slower, resource-heavy, optional
   Use for: application portals, dynamic pages, SPA (single-page apps)
   Requires: Playwright browsers installed (playwright install chromium)
   Enabled by: PLAYWRIGHT_ENABLED=true in .env

WHY CONVERT TO MARKDOWN?
LLMs work much better on clean text than raw HTML.
Raw HTML has thousands of tokens of navigation, ads, scripts, and styles
that are noise to the LLM and cost money to process.
Converting to Markdown removes all of that and keeps only the content.

WHAT IS httpx?
A modern async Python HTTP client — the async replacement for requests.
"Async" means while waiting for the server to respond, Python can do
other work (handle other fetch requests, process results, etc.)

CONTENT HASH:
We compute SHA256 of the page content and store it.
Next time we fetch the same URL, if the hash hasn't changed,
nothing on the page changed — no need to re-process.
This is how we detect when a university updates their deadline.
"""

import hashlib
import re
import time

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.tools.base import PageContent, PDFContent, ToolError, ToolErrorType

logger = structlog.get_logger(__name__)

# Headers that make us look like a normal browser
# Some university sites block requests with no User-Agent
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Domains known to block scrapers — we log a warning instead of failing hard
_KNOWN_BLOCKED_DOMAINS = {
    "linkedin.com",
    "facebook.com",
    "instagram.com",
}

# Max content size we'll process — 5MB is more than enough for a university page
_MAX_CONTENT_SIZE = 5 * 1024 * 1024  # 5MB


def _html_to_markdown(html: str, base_url: str = "") -> str:
    """
    Convert HTML to clean Markdown using BeautifulSoup.

    We do NOT use a full HTML-to-Markdown library because they produce
    noisy output with too many formatting artifacts. Instead we:
    1. Remove non-content elements (scripts, styles, nav, footer)
    2. Extract text with minimal formatting
    3. Clean up excessive whitespace

    This is intentionally simple — the LLM handles the rest.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ToolError(
            ToolErrorType.PARSE_ERROR,
            "beautifulsoup4 not installed",
        ) from e

    soup = BeautifulSoup(html, "lxml")

    # Remove elements that are never useful content
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "noscript", "iframe", "svg", "form",
                     "button", "input", "select", "textarea"]):
        tag.decompose()

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Get the main content — try common content containers first
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"content|main|body", re.I))
        or soup.find(class_=re.compile(r"content|main|body", re.I))
        or soup.body
        or soup
    )

    if not main:
        return title

    # Build markdown-like text
    lines = []
    if title:
        lines.append(f"# {title}\n")

    for element in main.descendants:
        if not hasattr(element, "name"):
            continue  # skip NavigableString directly

        name = element.name
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(name[1])
            text = element.get_text(strip=True)
            if text:
                lines.append(f"\n{'#' * level} {text}\n")
        elif name == "p":
            text = element.get_text(strip=True)
            if text and len(text) > 20:  # skip very short paragraphs (nav items etc)
                lines.append(f"\n{text}\n")
        elif name in ("li",):
            text = element.get_text(strip=True)
            if text:
                lines.append(f"- {text}")
        elif name in ("td", "th"):
            text = element.get_text(strip=True)
            if text:
                lines.append(f"| {text} ")

    markdown = "\n".join(lines)

    # Clean up: collapse multiple blank lines into one
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = markdown.strip()

    return markdown


def _compute_hash(content: str) -> str:
    """SHA256 hash of page content — used for change detection."""
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


@retry(
    retry=retry_if_exception_type(ToolError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    reraise=True,
)
def fetch_page(url: str) -> PageContent:
    """
    Fetch a web page and return its content as clean Markdown.

    Uses static HTTP fetch (httpx). For JavaScript-rendered pages,
    use fetch_page_rendered() instead.

    Args:
        url: The URL to fetch

    Returns:
        PageContent with markdown text ready for LLM processing

    Raises:
        ToolError: With specific type and retryable flag
    """
    if not url or not url.startswith(("http://", "https://")):
        raise ToolError(
            ToolErrorType.INVALID_INPUT,
            f"Invalid URL: {url!r}. Must start with http:// or https://",
        )

    settings = get_settings()

    # Check known blocked domains
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower().replace("www.", "")
    if domain in _KNOWN_BLOCKED_DOMAINS:
        logger.warning("fetch_page_blocked_domain", url=url, domain=domain)
        raise ToolError(
            ToolErrorType.ACCESS_DENIED,
            f"Domain {domain} is known to block automated access",
            url=url,
            retryable=False,
        )

    logger.info("fetch_page_started", url=url)
    start_time = time.time()

    try:
        with httpx.Client(
            headers=_BROWSER_HEADERS,
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            response = client.get(url)

    except httpx.TimeoutException as e:
        logger.warning("fetch_page_timeout", url=url)
        raise ToolError(
            ToolErrorType.NETWORK_ERROR,
            f"Request timed out after {settings.request_timeout_seconds}s: {url}",
            url=url,
            retryable=True,
        ) from e

    except httpx.ConnectError as e:
        logger.warning("fetch_page_connect_error", url=url, error=str(e))
        raise ToolError(
            ToolErrorType.NETWORK_ERROR,
            f"Connection failed: {url} — {e}",
            url=url,
            retryable=True,
        ) from e

    except Exception as e:
        logger.error("fetch_page_unexpected_error", url=url, error=str(e))
        raise ToolError(
            ToolErrorType.UNKNOWN,
            f"Unexpected error fetching {url}: {e}",
            url=url,
            retryable=False,
        ) from e

    # Handle HTTP error codes
    if response.status_code == 404:
        raise ToolError(
            ToolErrorType.NOT_FOUND,
            f"Page not found (404): {url}",
            url=url,
            status_code=404,
            retryable=False,
        )
    if response.status_code in (401, 403):
        raise ToolError(
            ToolErrorType.ACCESS_DENIED,
            f"Access denied ({response.status_code}): {url}",
            url=url,
            status_code=response.status_code,
            retryable=False,
        )
    if response.status_code == 429:
        raise ToolError(
            ToolErrorType.RATE_LIMITED,
            f"Rate limited (429): {url}",
            url=url,
            status_code=429,
            retryable=True,
        )
    if response.status_code >= 500:
        raise ToolError(
            ToolErrorType.EXTERNAL_API_ERROR,
            f"Server error ({response.status_code}): {url}",
            url=url,
            status_code=response.status_code,
            retryable=True,  # server errors are often transient
        )
    if response.status_code >= 400:
        raise ToolError(
            ToolErrorType.EXTERNAL_API_ERROR,
            f"HTTP error ({response.status_code}): {url}",
            url=url,
            status_code=response.status_code,
            retryable=False,
        )

    content_type = response.headers.get("content-type", "")
    elapsed_ms = (time.time() - start_time) * 1000

    # Check if it's a PDF — handle separately
    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        logger.info("fetch_page_detected_pdf", url=url)
        return _handle_pdf_response(url, response.content)

    # Check content size
    if len(response.content) > _MAX_CONTENT_SIZE:
        logger.warning("fetch_page_too_large", url=url, size=len(response.content))
        # Still process it but truncate
        raw_html = response.text[:_MAX_CONTENT_SIZE]
    else:
        raw_html = response.text

    # Convert to markdown
    try:
        markdown = _html_to_markdown(raw_html, base_url=url)
    except Exception as e:
        raise ToolError(
            ToolErrorType.PARSE_ERROR,
            f"Failed to parse HTML from {url}: {e}",
            url=url,
            retryable=False,
        ) from e

    # Extract title from markdown (first # line)
    title = None
    for line in markdown.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    word_count = len(markdown.split())

    logger.info(
        "fetch_page_completed",
        url=url,
        status_code=response.status_code,
        word_count=word_count,
        elapsed_ms=round(elapsed_ms, 1),
    )

    return PageContent(
        url=url,
        title=title,
        markdown=markdown,
        raw_html=raw_html,
        status_code=response.status_code,
        content_type=content_type,
        word_count=word_count,
        is_pdf=False,
    )


def _handle_pdf_response(url: str, content: bytes) -> PageContent:
    """Called when fetch_page detects a PDF content type."""
    pdf = fetch_pdf_bytes(url, content)
    return PageContent(
        url=url,
        title=pdf.title,
        markdown=pdf.text,
        raw_html=None,
        status_code=200,
        content_type="application/pdf",
        word_count=pdf.word_count,
        is_pdf=True,
    )


def fetch_pdf(url: str) -> PDFContent:
    """
    Fetch and extract text from a PDF at the given URL.

    Args:
        url: Direct URL to a PDF file

    Returns:
        PDFContent with extracted text
    """
    logger.info("fetch_pdf_started", url=url)

    try:
        with httpx.Client(
            headers=_BROWSER_HEADERS,
            timeout=get_settings().request_timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ToolError(
            ToolErrorType.EXTERNAL_API_ERROR,
            f"HTTP {e.response.status_code} fetching PDF: {url}",
            url=url,
            retryable=e.response.status_code >= 500,
        ) from e
    except Exception as e:
        raise ToolError(
            ToolErrorType.NETWORK_ERROR,
            f"Failed to fetch PDF {url}: {e}",
            url=url,
            retryable=True,
        ) from e

    return fetch_pdf_bytes(url, response.content)


def fetch_pdf_bytes(url: str, content: bytes) -> PDFContent:
    """
    Extract text from PDF bytes (already downloaded).

    WHY PyMuPDF (fitz)?
    - Fast and accurate
    - Handles most PDF encodings
    - Extracts text with layout awareness
    - Free and open source
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ToolError(
            ToolErrorType.PARSE_ERROR,
            "PyMuPDF not installed. Run: pip install pymupdf",
        ) from e

    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise ToolError(
            ToolErrorType.PARSE_ERROR,
            f"Cannot open PDF from {url}: {e}",
            url=url,
            retryable=False,
        ) from e

    pages_text = []
    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            pages_text.append(page.get_text())
        except Exception as e:
            logger.warning("pdf_page_extract_failed", url=url, page=page_num, error=str(e))
            continue

    doc.close()

    full_text = "\n\n".join(pages_text).strip()
    # Clean up excessive whitespace common in PDFs
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    full_text = re.sub(r" {2,}", " ", full_text)

    word_count = len(full_text.split())

    logger.info(
        "fetch_pdf_completed",
        url=url,
        pages=len(pages_text),
        word_count=word_count,
    )

    return PDFContent(
        url=url,
        title=None,  # PDFs rarely have reliable titles
        text=full_text,
        page_count=len(pages_text),
        word_count=word_count,
    )


def fetch_page_rendered(url: str) -> PageContent:
    """
    Fetch a JavaScript-rendered page using Playwright.

    Only called when PLAYWRIGHT_ENABLED=true in .env AND
    the static fetch returned insufficient content.

    This is slower (2-5 seconds per page) and requires
    Playwright browsers to be installed:
        python -m playwright install chromium

    Args:
        url: URL of the JS-rendered page

    Returns:
        PageContent with markdown from rendered HTML
    """
    settings = get_settings()

    if not settings.playwright_enabled:
        raise ToolError(
            ToolErrorType.INVALID_INPUT,
            "Playwright is disabled. Set PLAYWRIGHT_ENABLED=true in .env "
            "and run: python -m playwright install chromium",
            retryable=False,
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise ToolError(
            ToolErrorType.INVALID_INPUT,
            "playwright not installed. Run: pip install playwright && "
            "python -m playwright install chromium",
        ) from e

    logger.info("fetch_page_rendered_started", url=url)
    start_time = time.time()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(extra_http_headers=_BROWSER_HEADERS)
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            browser.close()
    except Exception as e:
        raise ToolError(
            ToolErrorType.NETWORK_ERROR,
            f"Playwright failed for {url}: {e}",
            url=url,
            retryable=True,
        ) from e

    elapsed_ms = (time.time() - start_time) * 1000
    markdown = _html_to_markdown(html, base_url=url)
    word_count = len(markdown.split())

    title = None
    for line in markdown.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    logger.info(
        "fetch_page_rendered_completed",
        url=url,
        word_count=word_count,
        elapsed_ms=round(elapsed_ms, 1),
    )

    return PageContent(
        url=url,
        title=title,
        markdown=markdown,
        raw_html=html,
        status_code=200,
        content_type="text/html",
        word_count=word_count,
        is_pdf=False,
    )
