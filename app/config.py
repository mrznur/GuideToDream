"""
app/config.py
─────────────
Central configuration for GuideToDream.

All settings are read from environment variables (loaded from .env in
development). Pydantic-Settings validates types and raises a clear error
at startup if anything required is missing.

Why this pattern?
- Single source of truth for all config
- Type-safe (pydantic validates and coerces types)
- Fail-fast (app won't start with broken config)
- No secrets in code — only in environment
- Easy to swap values between dev/staging/production
"""

from enum import Enum
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    All application settings, loaded from environment variables.
    Fields with no default are REQUIRED — the app will not start without them.
    Fields with defaults are optional.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # silently ignore unknown env vars
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_env: Environment = Environment.DEVELOPMENT
    app_secret_key: str = Field(default="dev-secret-change-in-production")
    log_level: str = Field(default="INFO")

    @computed_field  # type: ignore[misc]
    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(
        ...,  # required — no default
        description="Async SQLAlchemy connection string (postgresql+asyncpg://...)",
    )
    database_url_sync: str = Field(
        ...,
        description="Sync connection string for Alembic (postgresql+psycopg2://...)",
    )
    database_pool_size: int = Field(default=5)
    database_max_overflow: int = Field(default=10)
    database_echo: bool = Field(default=False)  # set True to log all SQL queries

    # -------------------------------------------------------------------------
    # LLM — Google Gemini
    # -------------------------------------------------------------------------
    gemini_api_key: str = Field(
        ...,
        description="Google Gemini API key from aistudio.google.com",
    )
    llm_fast_model: str = Field(
        default="gemini/gemini-3.6-flash",
        description="Cheap/fast model for routine tasks",
    )
    llm_smart_model: str = Field(
        default="gemini/gemini-3.6-flash",
        description="Smarter model for complex reasoning",
    )
    llm_max_retries: int = Field(default=3)
    llm_timeout_seconds: int = Field(default=60)

    # -------------------------------------------------------------------------
    # Web Search — Tavily
    # -------------------------------------------------------------------------
    tavily_api_key: str = Field(
        default="",
        description="Tavily API key (1000 free searches/month)",
    )

    # -------------------------------------------------------------------------
    # Notifications — Telegram
    # -------------------------------------------------------------------------
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    @computed_field  # type: ignore[misc]
    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    # Frontend
    frontend_url: str = Field(default="", description="Vercel frontend URL for CORS")

    # -------------------------------------------------------------------------
    # Single-user identity
    # -------------------------------------------------------------------------
    user_email: str = Field(
        default="mahmudunmiraz@gmail.com",
        description="The single owner's email — used to scope all DB queries",
    )

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    api_secret_key: str = Field(
        default="",
        description=(
            "Secret key that callers must send as X-API-Key header. "
            "Leave empty to disable auth (dev only). Set in production."
        ),
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Max requests per IP per minute (0 = disabled)",
    )

    # -------------------------------------------------------------------------
    # Web Research
    # -------------------------------------------------------------------------    playwright_enabled: bool = Field(default=False)
    request_timeout_seconds: int = Field(default=20)
    request_max_retries: int = Field(default=2)
    crawl_delay_seconds: float = Field(default=0.8)

    # -------------------------------------------------------------------------
    # Research / Scheduling
    # -------------------------------------------------------------------------
    notification_score_threshold: float = Field(default=70.0)
    deadline_reminder_days: int = Field(default=30)

    # Scheduling
    scheduler_enabled: bool = Field(default=True)
    research_schedule_hour: int = Field(default=8)
    research_schedule_minute: int = Field(default=0)
    deadline_check_hour: int = Field(default=14)
    deadline_check_minute: int = Field(default=0)
    daily_summary_hour: int = Field(default=21)
    daily_summary_minute: int = Field(default=0)


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using lru_cache means the .env file is only read once per process,
    not on every request. The cache is cleared in tests by calling
    get_settings.cache_clear().
    """
    return Settings()
