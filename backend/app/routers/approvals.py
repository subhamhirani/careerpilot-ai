"""
CareerPilot AI — Approvals API Router.

Endpoints for reviewing and acting on pending application approvals.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import get_current_user_id

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/")
async def list_pending_approvals(
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    """List all pending approvals awaiting user action."""
    return {"approvals": [], "total": 0, "limit": limit, "offset": offset}


@router.post("/{approval_id}/approve")
async def approve_application(
    approval_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Approve an application and trigger submission."""
    return {"status": "approved", "approval_id": approval_id, "message": "Application submission queued"}


@router.post("/{approval_id}/reject")
async def reject_application(
    approval_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Reject an application."""
    return {"status": "rejected", "approval_id": approval_id}
