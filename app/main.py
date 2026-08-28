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
    """
    Lifespan context manager — runs code on startup and shutdown.

    Everything before 'yield' runs when the app starts.
    Everything after 'yield' runs when the app shuts down.

    This replaces the old @app.on_event("startup") pattern.
    """
    settings = get_settings()

    # Set up logging first so all subsequent startup messages are captured
    setup_logging(settings.log_level)

    logger.info(
        "guidetodream_starting",
        environment=settings.app_env.value,
        log_level=settings.log_level,
    )

    # TODO (Milestone 3): initialize web research tools
    # TODO (Milestone 6): initialize LLM client
    # TODO (Milestone 10): start scheduler

    logger.info("guidetodream_ready")

    yield  # App is running — handle requests here

    # Shutdown
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

    return app


app = create_app()
