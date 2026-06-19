"""
CareerPilot AI — Match Scores API Router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import get_current_user_id

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/")
async def list_matches(
    tier: str | None = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    """List match scores for the current user."""
    return {"matches": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/{match_id}")
async def get_match(match_id: str, user_id: str = Depends(get_current_user_id)):
    """Get detailed match breakdown."""
    return {"match_id": match_id, "message": "Not yet implemented"}


@router.post("/re-rank")
async def re_rank_matches(user_id: str = Depends(get_current_user_id)):
    """Trigger a re-ranking of all unmatched jobs."""
    return {"status": "re_rank_triggered", "message": "Re-ranking started"}
