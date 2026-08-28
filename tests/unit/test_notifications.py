"""
tests/unit/test_notifications.py
──────────────────────────────────
Tests for the notification service.

We test:
1. Message formatting (no Telegram API calls)
2. Suppression logic concepts
3. Telegram disabled behavior
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.notification_service import (
    _format_deadline_reminder,
    _format_new_opportunity,
    send_telegram_message,
)


def make_mock_opportunity(
    programme_name="MSc Computer Science",
    university_name="TU Berlin",
    country="Germany",
    score=85.0,
    eligibility="eligible",
    tuition=0,
    deadline_days=45,
    score_explanation="Strong match: free tuition, CS background matches.",
    official_url="https://example.com/msc-cs",
):
    """Build a mock Opportunity object for testing formatters."""
    opp = MagicMock()
    opp.total_score = score
    opp.eligibility_status = eligibility
    opp.score_explanation = score_explanation
    opp.is_notable_change = False

    deadline = date.today() + timedelta(days=deadline_days) if deadline_days else None
    opp.application_deadline = deadline
    opp.scholarship_deadline = None

    prog = MagicMock()
    prog.name = programme_name
    prog.tuition_eur_per_year = tuition
    prog.official_url = official_url
    prog.application_portal_url = None

    uni = MagicMock()
    uni.name = university_name
    uni.country = country

    prog.university = uni
    opp.programme = prog
    return opp


class TestMessageFormatting:

    def test_new_opportunity_contains_programme_name(self):
        opp = make_mock_opportunity(programme_name="MSc AI Systems")
        msg = _format_new_opportunity(opp)
        assert "MSc AI Systems" in msg

    def test_new_opportunity_contains_score(self):
        opp = make_mock_opportunity(score=87.0)
        msg = _format_new_opportunity(opp)
        assert "87" in msg

    def test_new_opportunity_free_tuition_label(self):
        opp = make_mock_opportunity(tuition=0)
        msg = _format_new_opportunity(opp)
        assert "Free" in msg

    def test_new_opportunity_contains_university(self):
        opp = make_mock_opportunity(university_name="Charles University")
        msg = _format_new_opportunity(opp)
        assert "Charles University" in msg

    def test_new_opportunity_contains_deadline(self):
        opp = make_mock_opportunity(deadline_days=30)
        msg = _format_new_opportunity(opp)
        assert str(date.today() + timedelta(days=30)) in msg

    def test_new_opportunity_contains_url(self):
        opp = make_mock_opportunity(official_url="https://uni.example.com/msc")
        msg = _format_new_opportunity(opp)
        assert "uni.example.com" in msg

    def test_deadline_reminder_contains_days_left(self):
        opp = make_mock_opportunity(deadline_days=12)
        msg = _format_deadline_reminder(opp)
        assert "12 days" in msg

    def test_deadline_reminder_urgent_emoji(self):
        """Deadlines within 7 days should show the urgent emoji."""
        opp = make_mock_opportunity(deadline_days=5)
        msg = _format_deadline_reminder(opp)
        assert "🚨" in msg

    def test_deadline_reminder_non_urgent_emoji(self):
        opp = make_mock_opportunity(deadline_days=20)
        msg = _format_deadline_reminder(opp)
        assert "⏰" in msg

    def test_message_is_non_empty(self):
        opp = make_mock_opportunity()
        assert len(_format_new_opportunity(opp)) > 50
        assert len(_format_deadline_reminder(opp)) > 30


class TestTelegramSender:

    def test_returns_false_when_disabled(self):
        """When Telegram is not configured, send returns False gracefully."""
        with patch("app.services.notification_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.telegram_enabled = False
            mock_settings.return_value = settings
            result = send_telegram_message("test message")
            assert result is False

    def test_never_raises(self):
        """send_telegram_message must never raise an exception."""
        with patch("app.services.notification_service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.telegram_enabled = True
            settings.telegram_bot_token = "invalid_token"
            settings.telegram_chat_id = "12345"
            mock_settings.return_value = settings
            # Should return False, not raise
            result = send_telegram_message("test")
            assert isinstance(result, bool)
