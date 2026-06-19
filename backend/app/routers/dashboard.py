"""
CareerPilot AI — Dashboard & Analytics API Router.

Provides /dashboard/stats and /analytics endpoints that aggregate
data from the in-memory stores used by the resumes, jobs, and
applications routers.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from ..auth import get_current_user_id
from ..state import get_resumes

router = APIRouter(tags=["dashboard"])


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

@router.get("/dashboard/stats")
async def get_dashboard_stats(user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """Return high-level statistics for the current user's dashboard."""
    user_resumes = [r for r in get_resumes() if r["user_id"] == user_id]

    return {
        "total_jobs_found": 0,
        "total_applications_sent": 0,
        "pending_approvals": 0,
        "interview_rate": 0.0,
        "top_matches": [],
        "recent_activity": [
            {
                "id": "activity-1",
                "type": "job_found",
                "message": f"You have {len(user_resumes)} resume(s) uploaded. "
                           "Start the job discovery pipeline to find matching roles.",
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }
        ] if user_resumes else [
            {
                "id": "activity-welcome",
                "type": "job_found",
                "message": "Welcome to CareerPilot! Upload your resume to get started.",
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }
        ],
    }


# ─── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def get_analytics(user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """Return analytics data for the current user."""
    return {
        "match_trends": [],
        "source_breakdown": [
            {"source": "LinkedIn", "count": 0, "applications": 0},
            {"source": "Naukri", "count": 0, "applications": 0},
            {"source": "Indeed", "count": 0, "applications": 0},
        ],
        "funnel": [
            {"stage": "Jobs Discovered", "count": 0},
            {"stage": "Matched", "count": 0},
            {"stage": "Applied", "count": 0},
            {"stage": "Interview", "count": 0},
            {"stage": "Offer", "count": 0},
        ],
        "total_jobs": 0,
        "total_applications": 0,
        "approval_rate": 0.0,
        "interview_conversion": 0.0,
    }
