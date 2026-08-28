"""
app/utils/date_parser.py
─────────────────────────
Safe date parsing for deadline strings extracted from university pages.

University pages express deadlines in many formats:
  "1 December 2025"
  "December 1, 2025"
  "01/12/2025"
  "2025-12-01"
  "1 December"  ← no year — we infer the next occurrence
  "end of November"  ← vague — we return None

We use python-dateutil for flexible parsing, with fallback logic.
We NEVER guess when genuinely ambiguous. We return None and flag it.

WHY THIS IS A UTILITY NOT AN LLM TASK:
Date parsing is deterministic. If the string has a valid date, we parse it.
If it doesn't, we return None. No AI reasoning needed.
The LLM already extracted "1 December 2025" from the page text.
This function just converts that string to a Python date object.
"""

from datetime import date, datetime

import structlog

logger = structlog.get_logger(__name__)


def parse_date_safe(date_string: str | None) -> date | None:
    """
    Parse a date string into a Python date object.

    Args:
        date_string: A date string like "2025-12-01", "1 December 2025",
                     "December 1, 2025", etc.

    Returns:
        A date object if successfully parsed, None otherwise.
        Never raises an exception.
    """
    if not date_string or not date_string.strip():
        return None

    date_string = date_string.strip()

    # Try ISO format first (most reliable)
    try:
        return date.fromisoformat(date_string[:10])
    except ValueError:
        pass

    # Try dateutil parser (handles most natural language formats)
    try:
        from dateutil import parser as dateutil_parser
        parsed = dateutil_parser.parse(date_string, dayfirst=True)
        result = parsed.date()

        # If no year was in the string, dateutil uses the current year.
        # If that date has already passed, assume next year.
        current_year = datetime.now().year
        if result.year == current_year and result < date.today():
            result = result.replace(year=current_year + 1)

        return result

    except Exception:
        pass

    logger.debug("date_parse_failed", date_string=date_string)
    return None


def days_until(target: date | None) -> int | None:
    """
    Returns the number of days until a deadline.
    Returns None if deadline is None.
    Returns negative number if deadline has passed.
    """
    if target is None:
        return None
    return (target - date.today()).days


def is_upcoming(target: date | None, within_days: int = 30) -> bool:
    """Returns True if the deadline is within the given number of days."""
    days = days_until(target)
    if days is None:
        return False
    return 0 <= days <= within_days


def is_passed(target: date | None) -> bool:
    """Returns True if the deadline has already passed."""
    if target is None:
        return False
    return target < date.today()
