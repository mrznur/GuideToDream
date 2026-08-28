"""
app/services/notification_service.py
─────────────────────────────────────
Decides when to notify the user and sends notifications via Telegram.

NOTIFICATION PHILOSOPHY (from architecture doc):
  Never spam. Only notify when:
  1. A new high-scoring opportunity is discovered (score ≥ threshold)
  2. A material change occurred (deadline changed, scholarship added)
  3. A deadline is approaching (within 30 days, not yet notified today)
  4. An application has been in "preparing" state too long

SUPPRESSION LOGIC:
  Before sending any notification, check:
  - Was this opportunity notified about in the last N days?
  - Has the user already been notified today about deadlines?
  Suppression prevents the user from ignoring notifications because they
  see them too often.

TELEGRAM MESSAGE FORMAT:
  Telegram supports MarkdownV2 formatting but it requires escaping
  special characters. We keep messages simple and readable.
"""

import re
from datetime import datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.notification import Notification
from app.models.opportunity import Opportunity
from app.models.programme import Programme
from app.utils.date_parser import days_until

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Telegram sender
# ─────────────────────────────────────────────────────────────────────────────

def _escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.
    Characters that must be escaped: . ! ( ) - = + { } | # > ~
    """
    special = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special)}])', r'\\\1', text)


def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    """
    Send a message to the configured Telegram chat.

    We use HTML parse mode (simpler escaping than MarkdownV2).
    Returns True if sent successfully, False otherwise.
    Never raises — notification failure should not crash the pipeline.
    """
    settings = get_settings()

    if not settings.telegram_enabled:
        logger.debug("telegram_disabled", message=text[:50])
        return False

    try:
        import httpx
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        response = httpx.post(
            url,
            json={
                "chat_id": settings.telegram_chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if response.status_code == 200:
            logger.info("telegram_sent", chars=len(text))
            return True
        else:
            logger.warning(
                "telegram_failed",
                status=response.status_code,
                body=response.text[:200],
            )
            return False
    except Exception as e:
        logger.error("telegram_error", error=str(e))
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Message formatters
# ─────────────────────────────────────────────────────────────────────────────

def _format_new_opportunity(opp: Opportunity) -> str:
    """Format a 'new opportunity discovered' notification."""
    prog = opp.programme
    uni = prog.university if prog else None

    prog_name = prog.name if prog else "Unknown Programme"
    uni_name = uni.name if uni else "Unknown University"
    country = uni.country if uni else "?"
    tuition = prog.tuition_eur_per_year if prog else None
    score = opp.total_score or 0
    eligibility = opp.eligibility_status.replace("_", " ").title()

    tuition_str = "Free" if tuition == 0 else (f"€{tuition:,}/yr" if tuition else "Unknown")
    deadline_str = str(opp.application_deadline) if opp.application_deadline else "Unknown"
    days = days_until(opp.application_deadline)
    deadline_note = f" ({days} days left)" if days and days > 0 else ""

    url = prog.official_url if prog else None
    url_line = f'\n🔗 <a href="{url}">Official page</a>' if url else ""

    return (
        f"🎓 <b>New Opportunity Found!</b>\n\n"
        f"<b>{prog_name}</b>\n"
        f"🏛 {uni_name}, {country}\n"
        f"💰 Tuition: {tuition_str}\n"
        f"📅 Deadline: {deadline_str}{deadline_note}\n"
        f"✅ Eligibility: {eligibility}\n"
        f"⭐ Score: {score:.0f}/100\n"
        f"{url_line}\n\n"
        f"<i>{opp.score_explanation.split(chr(10))[0] if opp.score_explanation else ''}</i>"
    )


def _format_deadline_reminder(opp: Opportunity) -> str:
    """Format a deadline reminder notification."""
    prog = opp.programme
    uni = prog.university if prog else None

    prog_name = prog.name if prog else "Unknown Programme"
    uni_name = uni.name if uni else "Unknown University"
    days = days_until(opp.application_deadline)
    score = opp.total_score or 0
    url = prog.application_portal_url or (prog.official_url if prog else None)
    url_line = f'\n🔗 <a href="{url}">Apply here</a>' if url else ""

    urgency = "🚨" if days and days <= 7 else "⏰"

    return (
        f"{urgency} <b>Deadline Reminder</b>\n\n"
        f"<b>{prog_name}</b>\n"
        f"🏛 {uni_name}\n"
        f"📅 Deadline: <b>{opp.application_deadline}</b> ({days} days left)\n"
        f"⭐ Your score: {score:.0f}/100\n"
        f"{url_line}"
    )


def _format_material_change(opp: Opportunity, change_notes: str) -> str:
    """Format a material change notification."""
    prog = opp.programme
    prog_name = prog.name if prog else "Unknown Programme"
    uni = prog.university if prog else None
    uni_name = uni.name if uni else "Unknown University"

    return (
        f"🔄 <b>Programme Update</b>\n\n"
        f"<b>{prog_name}</b> @ {uni_name}\n\n"
        f"What changed: {change_notes}\n\n"
        f"⭐ Updated score: {opp.total_score:.0f}/100"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Suppression check
# ─────────────────────────────────────────────────────────────────────────────

async def _was_recently_notified(
    db: AsyncSession,
    user_id,
    opportunity_id,
    notification_type: str,
    within_days: int = 7,
) -> bool:
    """
    Check if we already sent this type of notification for this opportunity
    within the suppression window.
    """
    cutoff = datetime.utcnow() - timedelta(days=within_days)
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.opportunity_id == opportunity_id,
            Notification.notification_type == notification_type,
            Notification.sent_at >= cutoff,
        )
    )
    return result.scalar_one_or_none() is not None


async def _log_notification(
    db: AsyncSession,
    user_id,
    opportunity_id,
    notification_type: str,
    message: str,
    channel: str = "telegram",
    sent: bool = True,
):
    """Log a notification to the database."""
    notification = Notification(
        user_id=user_id,
        opportunity_id=opportunity_id,
        notification_type=notification_type,
        channel=channel,
        message=message,
        sent_at=datetime.utcnow() if sent else None,
    )
    db.add(notification)
    await db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# Main notification evaluation
# ─────────────────────────────────────────────────────────────────────────────

async def evaluate_and_notify(
    db: AsyncSession,
    user_id,
    opportunity: Opportunity,
    is_new: bool = False,
) -> bool:
    """
    Evaluate whether to send a notification for this opportunity.
    Sends the notification if warranted.

    Returns True if a notification was sent.
    """
    settings = get_settings()
    sent = False

    # ── New high-scoring opportunity ─────────────────────────────────────
    if is_new and opportunity.total_score and \
       opportunity.total_score >= settings.notification_score_threshold:

        already_notified = await _was_recently_notified(
            db, user_id, opportunity.id, "new_opportunity", within_days=30
        )
        if not already_notified:
            message = _format_new_opportunity(opportunity)
            sent = send_telegram_message(message)
            await _log_notification(
                db, user_id, opportunity.id,
                "new_opportunity", message, sent=sent,
            )
            logger.info(
                "notification_new_opportunity",
                programme=opportunity.programme.name if opportunity.programme else "?",
                score=opportunity.total_score,
                sent=sent,
            )

    # ── Material change ──────────────────────────────────────────────────
    elif opportunity.is_notable_change and not is_new:
        already_notified = await _was_recently_notified(
            db, user_id, opportunity.id, "material_change", within_days=3
        )
        if not already_notified:
            message = _format_material_change(opportunity, "Score or deadline updated")
            sent = send_telegram_message(message)
            await _log_notification(
                db, user_id, opportunity.id,
                "material_change", message, sent=sent,
            )

    # ── Deadline reminder ────────────────────────────────────────────────
    days = days_until(opportunity.application_deadline)
    if days is not None and 0 < days <= settings.deadline_reminder_days:
        if opportunity.eligibility_status != "ineligible":
            already_notified = await _was_recently_notified(
                db, user_id, opportunity.id, "deadline_reminder", within_days=1
            )
            if not already_notified:
                message = _format_deadline_reminder(opportunity)
                sent_deadline = send_telegram_message(message)
                await _log_notification(
                    db, user_id, opportunity.id,
                    "deadline_reminder", message, sent=sent_deadline,
                )
                sent = sent or sent_deadline
                logger.info(
                    "notification_deadline",
                    programme=opportunity.programme.name if opportunity.programme else "?",
                    days_left=days,
                    sent=sent_deadline,
                )

    return sent


async def send_daily_summary(
    db: AsyncSession,
    user_id,
    top_opportunities: list[Opportunity],
) -> bool:
    """
    Send a daily summary of top opportunities and upcoming deadlines.
    Called by the scheduler at a configured time each day.
    """
    if not top_opportunities:
        return False

    lines = ["📊 <b>GuideToDream Daily Summary</b>\n"]

    # Top 3 by score
    top3 = sorted(
        [o for o in top_opportunities if o.eligibility_status != "ineligible"],
        key=lambda x: x.total_score or 0,
        reverse=True,
    )[:3]

    if top3:
        lines.append("<b>Top Opportunities:</b>")
        for i, opp in enumerate(top3, 1):
            prog = opp.programme
            uni = prog.university if prog else None
            name = prog.name if prog else "?"
            school = uni.name if uni else "?"
            lines.append(f"{i}. {name} @ {school} — {opp.total_score:.0f}/100")
        lines.append("")

    # Upcoming deadlines
    urgent = [
        o for o in top_opportunities
        if days_until(o.application_deadline) is not None
        and 0 < (days_until(o.application_deadline) or 999) <= 30
        and o.eligibility_status != "ineligible"
    ]
    if urgent:
        lines.append("<b>Upcoming Deadlines:</b>")
        for opp in sorted(urgent, key=lambda x: x.application_deadline or "9999"):
            prog = opp.programme
            name = prog.name if prog else "?"
            days = days_until(opp.application_deadline)
            lines.append(f"⏰ {name} — {days} days left ({opp.application_deadline})")

    message = "\n".join(lines)
    sent = send_telegram_message(message)

    if sent:
        await _log_notification(
            db, user_id, None,
            "daily_summary", message, sent=True,
        )

    return sent
