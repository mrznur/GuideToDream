"""
app/database.py
───────────────
Database engine, session factory, and base model setup.

Concepts taught here:
- SQLAlchemy async engine: manages the connection pool to PostgreSQL
- AsyncSession: a database session — think of it as a "unit of work"
  that groups related queries into one transaction
- get_db(): a FastAPI dependency that provides a session per request
  and ensures it's closed after the request finishes
- Base: the declarative base that all ORM models inherit from

Why async?
Our agent makes many I/O-bound calls (LLM, web fetch, database).
Using async means while one operation is waiting for a response,
the event loop can handle other work — important for performance.
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
    """
    All SQLAlchemy ORM models inherit from this Base.
    It keeps a registry of all models, which Alembic uses to
    generate migrations automatically.
    """
    pass


def create_engine():
    """
    Creates the async SQLAlchemy engine.

    The engine manages a connection pool — a set of reusable database
    connections. Rather than opening a new TCP connection to PostgreSQL
    on every query (expensive), we reuse connections from the pool.

    pool_size: number of connections to keep open permanently
    max_overflow: extra connections allowed beyond pool_size under load
    echo: if True, prints every SQL statement — useful for debugging
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.database_echo,
        # Supabase closes idle connections after a while.
        # pool_pre_ping sends a lightweight "SELECT 1" before using a
        # connection to verify it's still alive.
        pool_pre_ping=True,
    )


# Module-level engine instance — created once when the module is imported
engine = create_engine()

# Session factory — call this to get a new AsyncSession
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # expire_on_commit=False means SQLAlchemy won't expire (clear) objects
    # after a commit. This is important in async code where you might want
    # to access attributes after committing without triggering another query.
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in a route:
        @router.get("/programmes")
        async def list_programmes(db: AsyncSession = Depends(get_db)):
            ...

    The 'async with' / 'yield' pattern ensures:
    1. A new session is created for each request
    2. The session is automatically closed after the request completes
    3. If an exception occurs, the session is still properly closed
    """
    async with AsyncSessionLocal() as session:
        yield session
