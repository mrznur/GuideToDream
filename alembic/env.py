"""
alembic/env.py
──────────────
Alembic migration environment.

Alembic reads this file to know:
1. How to connect to the database (sync connection via psycopg2)
2. Which models to inspect when generating migrations (via Base.metadata)

Why sync? Alembic itself is synchronous. It uses the DATABASE_URL_SYNC
connection string (psycopg2 driver) rather than the async one (asyncpg).
Your application uses asyncpg for performance; Alembic uses psycopg2
for simplicity. Both connect to the same Supabase database.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings

# Import Base and all models so Alembic knows about every table
# If you add a new model and forget to import it here (or in models/__init__.py),
# Alembic will not generate a migration for it.
from app.database import Base
import app.models  # noqa: F401 — imports all models into Base.metadata

# Alembic Config object — provides access to the .ini file values
config = context.config

# Set up Python logging from the alembic.ini logging section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that Alembic inspects to generate migrations
target_metadata = Base.metadata


def get_url() -> str:
    """Get the sync database URL from our settings."""
    return get_settings().database_url_sync


def run_migrations_offline() -> None:
    """
    Run migrations without a live database connection.
    Useful for generating SQL scripts to review before applying.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare server defaults so Alembic detects changes to
        # column defaults (like server_default=func.now())
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations with a live database connection.
    This is the normal path when you run: alembic upgrade head
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool: don't pool connections in migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
