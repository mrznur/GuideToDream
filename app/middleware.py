"""
app/middleware.py
─────────────────
Request middleware for GuideToDream.

Provides three things:
  1. API key authentication  — callers must send X-API-Key header
  2. IP-based rate limiting  — simple token-bucket, no Redis needed
  3. Request timeout         — kills slow requests so the server never hangs

WHY NOT USE A LIBRARY?
The project has no slowapi/limits dependency. A self-contained
implementation keeps the dependency count low and is trivial to audit.
"""

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)

# ─── Paths that are always public (no auth, no rate limit) ────────────────
_PUBLIC_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json"}


# ──────────────────────────────────────────────────────────────────────────
# 1. API Key Authentication
# ──────────────────────────────────────────────────────────────────────────
class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Require an X-API-Key header on every non-public request.

    If api_secret_key is empty the middleware is a no-op (useful for local dev
    without any auth setup, but should always be set in production).
    """

    def __init__(self, app: ASGIApp, api_key: str) -> None:
        super().__init__(app)
        self._key = api_key

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # No key configured → allow everything (dev mode)
        if not self._key:
            return await call_next(request)

        # Public paths always pass through
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # CORS preflight must pass through so the browser can negotiate
        if request.method == "OPTIONS":
            return await call_next(request)

        sent = request.headers.get("X-API-Key", "")
        if sent != self._key:
            logger.warning(
                "api_key_rejected",
                path=request.url.path,
                ip=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key. Send X-API-Key header."},
            )

        return await call_next(request)


# ──────────────────────────────────────────────────────────────────────────
# 2. Rate Limiting (token bucket per IP)
# ──────────────────────────────────────────────────────────────────────────
class _Bucket:
    """Simple token-bucket for one IP address."""
    __slots__ = ("tokens", "last_refill")

    def __init__(self, capacity: int) -> None:
        self.tokens: float = capacity
        self.last_refill: float = time.monotonic()

    def consume(self, capacity: int, per_seconds: float = 60.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        # Refill proportionally to elapsed time
        self.tokens = min(capacity, self.tokens + elapsed * (capacity / per_seconds))
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True  # allowed
        return False  # rate limited


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    IP-level rate limiting using a token bucket.
    Buckets are stored in-process memory — resets on restart.
    Good enough for a single-instance personal app.
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int) -> None:
        super().__init__(app)
        self._rpm = requests_per_minute
        self._buckets: dict[str, _Bucket] = defaultdict(lambda: _Bucket(requests_per_minute))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self._rpm <= 0:
            return await call_next(request)

        if request.url.path in _PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        bucket = self._buckets[ip]

        if not bucket.consume(self._rpm):
            logger.warning("rate_limit_hit", ip=ip, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Slow down."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


# ──────────────────────────────────────────────────────────────────────────
# 3. Request Timeout
# ──────────────────────────────────────────────────────────────────────────
class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Kill any request that takes longer than `timeout_seconds`.
    Prevents slow LLM or DB calls from holding connections indefinitely.
    """

    def __init__(self, app: ASGIApp, timeout_seconds: float = 60.0) -> None:
        super().__init__(app)
        self._timeout = timeout_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self._timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "request_timeout",
                path=request.url.path,
                timeout=self._timeout,
            )
            return JSONResponse(
                status_code=504,
                content={"detail": f"Request timed out after {self._timeout}s."},
            )
