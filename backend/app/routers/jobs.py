"""
CareerPilot AI — Jobs API Router.

Endpoints for browsing discovered job postings with filtering.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..auth import get_current_user_id
from ..state import get_jobs, add_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    tier: Optional[str] = Query(None, description="Filter by match tier"),
    source: Optional[str] = Query(None, description="Filter by source"),
    location: Optional[str] = Query(None, description="Filter by location"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
):
    """List job postings with optional filters."""
    return {
        "jobs": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{job_id}")
async def get_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a specific job posting with match details."""
    return {
        "job_id": job_id,
        "message": "Not yet implemented",
    }


@router.post("/{job_id}/save")
async def save_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    """Save/bookmark a job posting."""
    return {"status": "saved", "job_id": job_id}


@router.post("/{job_id}/reject")
async def reject_job(job_id: str, user_id: str = Depends(get_current_user_id)):
    """Reject/dismiss a job posting."""
    return {"status": "rejected", "job_id": job_id}
