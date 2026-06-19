"""
CareerPilot AI — Applications API Router.

Endpoints for tracking submitted applications and their status.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import get_current_user_id

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/")
async def list_applications(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    """List all submitted applications with status tracking."""
    return {"applications": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/{application_id}")
async def get_application(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get detailed status of a specific application."""
    return {"application_id": application_id, "message": "Not yet implemented"}


@router.get("/stats")
async def application_stats(user_id: str = Depends(get_current_user_id)):
    """Get aggregate application statistics."""
    return {
        "total": 0,
        "submitted": 0,
        "in_progress": 0,
        "replied": 0,
        "interview": 0,
        "rejected": 0,
        "accepted": 0,
    }
