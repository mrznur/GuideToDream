"""
app/main.py
───────────
FastAPI application entry point.

Middleware stack (outermost → innermost):
  CORSMiddleware → TimeoutMiddleware → RateLimitMiddleware → APIKeyMiddleware → route

Global exception handler converts unhandled exceptions to clean JSON
so stack traces never leak to callers in production.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.middleware import APIKeyMiddleware, RateLimitMiddleware, TimeoutMiddleware
from app.utils.logging import setup_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info(
        "guidetodream_starting",
        environment=settings.app_env.value,
        log_level=settings.log_level,
        auth_enabled=bool(settings.api_secret_key),
        rate_limit_rpm=settings.rate_limit_per_minute,
    )

    from app.scheduler.jobs import setup_scheduler
    scheduler = setup_scheduler()
    if settings.scheduler_enabled:
        scheduler.start()
        logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))

    logger.info("guidetodream_ready")
    yield

    if settings.scheduler_enabled and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    logger.info("guidetodream_shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="GuideToDream",
        description="Personal European Higher-Studies Agent",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Global exception handler ──────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        detail = str(exc) if settings.is_development else "An internal error occurred."
        return JSONResponse(status_code=500, content={"detail": detail})

    # ── CORS ──────────────────────────────────────────────────────────────
    # localhost always allowed so local dev can hit Render directly if needed.
    # frontend_url (Vercel) always allowed in production.
    # Wildcard in development mode for convenience.
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    if settings.frontend_url:
        allowed_origins.append(settings.frontend_url)
    if settings.is_development:
        allowed_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request timeout (60s hard limit per request) ──────────────────────
    app.add_middleware(TimeoutMiddleware, timeout_seconds=60.0)

    # ── Rate limiting ─────────────────────────────────────────────────────
    if settings.rate_limit_per_minute > 0:
        app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)

    # ── API key authentication ────────────────────────────────────────────
    app.add_middleware(APIKeyMiddleware, api_key=settings.api_secret_key)

    # ── Health check (always public) ──────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health_check():
        return {"status": "ok", "environment": settings.app_env.value}

    # ── Routers ───────────────────────────────────────────────────────────
    from app.api.research import router as research_router
    from app.api.opportunities import router as opportunities_router
    from app.api.applications import router as applications_router
    from app.api.assistant import router as assistant_router
    from app.api.notifications import router as notifications_router
    from app.api.schedule import router as schedule_router
    from app.api.admin import router as admin_router
    from app.api.preferences import router as preferences_router

    app.include_router(research_router,      prefix="/api/v1")
    app.include_router(opportunities_router, prefix="/api/v1")
    app.include_router(applications_router,  prefix="/api/v1")
    app.include_router(assistant_router,     prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(schedule_router,      prefix="/api/v1")
    app.include_router(admin_router,         prefix="/api/v1")
    app.include_router(preferences_router,   prefix="/api/v1")

    return app


app = create_app()
