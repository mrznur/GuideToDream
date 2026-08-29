"""
app/database.py
───────────────
Database engine, session factory, and base model setup.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """All SQLAlchemy ORM models inherit from this Base."""
    pass


def create_engine():
    """
    Creates the async SQLAlchemy engine.

    IMPORTANT: statement_cache_size=0 is required when using Supabase
    connection pooler (PgBouncer) in transaction mode (port 6543).
    PgBouncer does not support asyncpg's prepared statement caching.
    Without this setting, the second DB operation in a session raises:
      DuplicatePreparedStatementError: prepared statement already exists
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.database_echo,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )


engine = create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — provides one session per request."""
    async with AsyncSessionLocal() as session:
        yield session
