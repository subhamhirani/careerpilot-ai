"""
CareerPilot AI — Notification Service.
Creates in-app notifications for user events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory notification store (per container lifetime)
_notifications: list[dict] = []


def get_notifications(user_id: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
    """Get notifications for a user, newest first."""
    results = [n for n in _notifications if n["user_id"] == user_id]
    if unread_only:
        results = [n for n in results if not n["is_read"]]
    results.sort(key=lambda n: n["created_at"], reverse=True)
    return results[:limit]


def get_unread_count(user_id: str) -> int:
    """Get count of unread notifications for a user."""
    return sum(1 for n in _notifications if n["user_id"] == user_id and not n["is_read"])


def create_notification(
    user_id: str,
    type: str,
    title: str,
    message: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> dict:
    """Create a new notification."""
    import uuid as _uuid

    n = {
        "id": str(_uuid.uuid4()),
        "user_id": user_id,
        "type": type,
        "title": title,
        "message": message,
        "is_read": False,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _notifications.append(n)
    # Keep max 200 per user
    user_notes = [x for x in _notifications if x["user_id"] == user_id]
    if len(user_notes) > 200:
        to_remove = user_notes[:-200]
        for r in to_remove:
            _notifications.remove(r)
    logger.info("Notification created: %s for user %s", type, user_id)
    return n


def mark_as_read(notification_id: str, user_id: str) -> bool:
    """Mark a notification as read. Returns True if found."""
    for n in _notifications:
        if n["id"] == notification_id and n["user_id"] == user_id:
            n["is_read"] = True
            return True
    return False


def mark_all_as_read(user_id: str) -> int:
    """Mark all notifications as read for a user. Returns count updated."""
    count = 0
    for n in _notifications:
        if n["user_id"] == user_id and not n["is_read"]:
            n["is_read"] = True
            count += 1
    return count


def delete_notification(notification_id: str, user_id: str) -> bool:
    """Delete a notification. Returns True if found and deleted."""
    for i, n in enumerate(_notifications):
        if n["id"] == notification_id and n["user_id"] == user_id:
            _notifications.pop(i)
            return True
    return False
