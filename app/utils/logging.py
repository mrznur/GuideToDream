"""
app/utils/logging.py
────────────────────
Structured logging setup using structlog.

Why structured logging?
Normal logging: "ERROR: Failed to fetch page at 14:23:01"
Structured logging: {"level": "error", "event": "page_fetch_failed",
                     "url": "https://...", "attempt": 2, "timestamp": "..."}

The structured version is:
- Machine-readable (you can grep/filter by any field)
- Consistent (every log line has the same shape)
- Contextual (you can add request_id, run_id, etc. automatically)
- Ready to ship to a log aggregator (Loki, Datadog, etc.) later

The processor chain below transforms each log event through a series
of steps before it's rendered — adding timestamps, log levels,
filtering sensitive keys, and formatting the output.
"""

import logging
import sys

import structlog

# Fields that should never appear in logs
# (add API keys, passwords, PII here)
_SENSITIVE_FIELDS = {
    "password",
    "api_key",
    "gemini_api_key",
    "tavily_api_key",
    "telegram_bot_token",
    "database_url",
    "database_url_sync",
    "app_secret_key",
}


def _filter_sensitive(logger, method, event_dict):
    """
    Processor: removes sensitive fields from log events.
    Even if someone accidentally logs a settings object,
    the sensitive keys will be stripped.
    """
    for field in _SENSITIVE_FIELDS:
        if field in event_dict:
            event_dict[field] = "[REDACTED]"
    return event_dict


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog for the application.
    Call this once at startup from main.py.
    """
    # Configure the standard library logging as well
    # (some libraries use stdlib logging, we want those to go through structlog)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            # Add log level to the event dict
            structlog.stdlib.add_log_level,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Filter sensitive data
            _filter_sensitive,
            # Add caller info in development
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            # Render as JSON in production, pretty-print in development
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str = __name__):
    """
    Returns a structlog logger bound to the given name.

    Usage:
        logger = get_logger(__name__)
        logger.info("research_run_started", run_id=str(run.id), queries=5)
        logger.error("page_fetch_failed", url=url, attempt=2, error=str(e))
    """
    return structlog.get_logger(name)
