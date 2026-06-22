"""
CareerPilot AI — Notification API Router.
Endpoints for listing, reading, and managing notifications.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_current_user_id
from ..notification_service import (
    get_notifications,
    get_unread_count,
    mark_as_read,
    mark_all_as_read,
    delete_notification,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
):
    """List notifications for the current user."""
    notifications = get_notifications(user_id, unread_only=unread_only, limit=limit)
    unread = get_unread_count(user_id)
    return {"notifications": notifications, "unread_count": unread, "total": len(notifications)}


@router.get("/unread-count")
async def unread_count(user_id: str = Depends(get_current_user_id)):
    """Get the count of unread notifications."""
    return {"unread_count": get_unread_count(user_id)}


@router.post("/{notification_id}/read")
async def read_notification(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Mark a single notification as read."""
    if not mark_as_read(notification_id, user_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


@router.post("/read-all")
async def read_all_notifications(user_id: str = Depends(get_current_user_id)):
    """Mark all notifications as read."""
    count = mark_all_as_read(user_id)
    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
async def remove_notification(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a notification."""
    if not delete_notification(notification_id, user_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}
