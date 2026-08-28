"""
app/tools/web_search.py
────────────────────────
Web search tool using Tavily API.

WHY TAVILY over raw Google/Bing?
- Returns clean, structured results (title, url, snippet, score)
- Designed for LLM/agent use cases
- 1000 free searches/month
- No HTML parsing needed on our end

WHY NOT just use Google?
- Google's Search API is expensive ($5/1000 queries)
- Scraping Google search results violates their ToS
- Tavily handles all the hard parts and gives better structured output

RETRY STRATEGY:
We use tenacity for retries. The pattern:
- Transient errors (network timeout, rate limit): retry with exponential backoff
- Permanent errors (invalid API key, bad query): fail immediately, don't retry
- Log every retry attempt so you can see what's happening

WHAT IS EXPONENTIAL BACKOFF?
Instead of retrying immediately (which hammers a struggling API), we wait:
  attempt 1: wait 1 second
  attempt 2: wait 2 seconds
  attempt 3: wait 4 seconds
  attempt 4: give up
This gives the API time to recover.
"""

import time

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.tools.base import (
    SearchResponse,
    SearchResult,
    ToolError,
    ToolErrorType,
)

logger = structlog.get_logger(__name__)


def _get_tavily_client():
    """
    Lazily initialise the Tavily client.
    We import here (not at module level) so the module can be imported
    even if tavily-python is not installed yet during testing.
    """
    try:
        from tavily import TavilyClient
    except ImportError as e:
        raise ToolError(
            ToolErrorType.INVALID_INPUT,
            "tavily-python not installed. Run: pip install tavily-python",
        ) from e

    settings = get_settings()
    if not settings.tavily_api_key:
        raise ToolError(
            ToolErrorType.INVALID_INPUT,
            "TAVILY_API_KEY not set in environment. Get a free key at tavily.com",
        )
    return TavilyClient(api_key=settings.tavily_api_key)


# Retry decorator:
# - Retry up to 3 times total
# - Only retry on ToolError where retryable=True (network issues, rate limits)
# - Wait 2^attempt seconds between retries (2s, 4s, 8s)
@retry(
    retry=retry_if_exception_type(ToolError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def search_web(
    query: str,
    num_results: int = 10,
    search_depth: str = "basic",          # "basic" (fast) or "advanced" (thorough)
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> SearchResponse:
    """
    Search the web using Tavily and return structured results.

    Args:
        query: The search query string
        num_results: Number of results to return (max 20)
        search_depth: "basic" for speed, "advanced" for thoroughness
        include_domains: Only return results from these domains
        exclude_domains: Never return results from these domains

    Returns:
        SearchResponse with a list of SearchResult objects

    Raises:
        ToolError: With specific error type and retryable flag
    """
    if not query or not query.strip():
        raise ToolError(ToolErrorType.INVALID_INPUT, "Search query cannot be empty")

    query = query.strip()
    num_results = min(max(1, num_results), 20)  # clamp between 1 and 20

    logger.info(
        "web_search_started",
        query=query,
        num_results=num_results,
        search_depth=search_depth,
    )

    start_time = time.time()

    try:
        client = _get_tavily_client()

        kwargs: dict = {
            "query": query,
            "max_results": num_results,
            "search_depth": search_depth,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains

        raw = client.search(**kwargs)

    except ToolError:
        raise  # re-raise our own errors

    except Exception as e:
        error_msg = str(e).lower()

        # Detect rate limiting
        if "rate limit" in error_msg or "429" in error_msg or "quota" in error_msg:
            logger.warning("web_search_rate_limited", query=query, error=str(e))
            raise ToolError(
                ToolErrorType.RATE_LIMITED,
                f"Tavily rate limit hit: {e}",
                retryable=True,
            ) from e

        # Detect auth failures (don't retry — wrong key won't fix itself)
        if "401" in error_msg or "unauthorized" in error_msg or "invalid api" in error_msg:
            raise ToolError(
                ToolErrorType.ACCESS_DENIED,
                f"Tavily API key invalid or missing: {e}",
                retryable=False,
            ) from e

        # Network errors (transient — worth retrying)
        if "timeout" in error_msg or "connection" in error_msg or "network" in error_msg:
            logger.warning("web_search_network_error", query=query, error=str(e))
            raise ToolError(
                ToolErrorType.NETWORK_ERROR,
                f"Network error during search: {e}",
                retryable=True,
            ) from e

        # Unknown error
        logger.error("web_search_failed", query=query, error=str(e))
        raise ToolError(
            ToolErrorType.UNKNOWN,
            f"Unexpected search error: {e}",
            retryable=False,
        ) from e

    elapsed_ms = (time.time() - start_time) * 1000

    # Parse Tavily response into our clean types
    results = []
    for item in raw.get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                score=float(item.get("score", 0.0)),
                published_date=item.get("published_date"),
            )
        )

    response = SearchResponse(
        query=query,
        results=results,
        total_results=len(results),
        search_time_ms=elapsed_ms,
    )

    logger.info(
        "web_search_completed",
        query=query,
        results_found=len(results),
        elapsed_ms=round(elapsed_ms, 1),
    )

    return response
