"""
app/api/notifications.py
─────────────────────────
REST API for notifications — test sending and view history.
"""

from app.config import get_settings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import send_telegram_message

router = APIRouter(prefix="/notifications", tags=["notifications"])

_USER_EMAIL: str = get_settings().user_email


class TestMessageRequest(BaseModel):
    message: str = "👋 GuideToDream is connected! Notifications are working."


@router.post("/test")
async def send_test_notification(
    request: TestMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a test Telegram message to verify the bot is configured."""
    sent = send_telegram_message(request.message)
    if sent:
        return {"status": "sent", "message": request.message}
    return {"status": "failed", "detail": "Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"}


@router.get("/history")
async def get_notification_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get recent notification history."""
    user_result = await db.execute(select(User).where(User.email == _USER_EMAIL))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(desc(Notification.created_at))
        .limit(limit)
    )
    notifications = result.scalars().all()

    return [
        {
            "id": str(n.id),
            "type": n.notification_type,
            "channel": n.channel,
            "sent_at": str(n.sent_at) if n.sent_at else None,
            "message_preview": n.message[:100] + "..." if len(n.message) > 100 else n.message,
        }
        for n in notifications
    ]
