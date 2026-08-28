"""
app/main.py
───────────
FastAPI application entry point.

This file:
1. Creates the FastAPI app instance
2. Registers routers (API endpoints)
3. Sets up startup/shutdown lifecycle events
4. Configures logging

When you run: uvicorn app.main:app --reload
Python imports this file, creates the `app` object, and uvicorn
starts serving HTTP requests.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
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
    )

    # Start scheduler
    from app.scheduler.jobs import setup_scheduler
    scheduler = setup_scheduler()
    if settings.scheduler_enabled:
        scheduler.start()
        logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))

    logger.info("guidetodream_ready")

    yield  # App is running

    # Shutdown
    if settings.scheduler_enabled and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    logger.info("guidetodream_shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="GuideToDream",
        description="Personal European Higher-Studies Intelligence Agent",
        version="0.1.0",
        # Disable docs in production (they expose your API structure)
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS — for development, allow all origins
    # In production, restrict to your actual frontend URL
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint — used by deployment platforms to verify the app is running
    @app.get("/health", tags=["system"])
    async def health_check():
        return {"status": "ok", "environment": settings.app_env.value}

    # TODO (Milestone 2+): register routers
    # app.include_router(profile_router, prefix="/api/v1")
    # app.include_router(opportunities_router, prefix="/api/v1")
    from app.api.research import router as research_router
    from app.api.opportunities import router as opportunities_router
    from app.api.applications import router as applications_router
    from app.api.assistant import router as assistant_router
    from app.api.notifications import router as notifications_router
    from app.api.schedule import router as schedule_router

    app.include_router(research_router, prefix="/api/v1")
    app.include_router(opportunities_router, prefix="/api/v1")
    app.include_router(applications_router, prefix="/api/v1")
    app.include_router(assistant_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(schedule_router, prefix="/api/v1")

    return app


app = create_app()
