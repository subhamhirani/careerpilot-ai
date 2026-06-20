"""
CareerPilot AI — Dashboard & Analytics API Router.

Provides /dashboard/stats and /analytics endpoints that aggregate
data from the database.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from ..auth import get_current_user_id

router = APIRouter(tags=["dashboard"])


def _get_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


@router.get("/dashboard/stats")
async def get_dashboard_stats(user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Return high-level statistics for the current user's dashboard."""
    uid = user_id

    # Count resumes
    resume_count = db.execute(
        text("SELECT COUNT(*) FROM resumes WHERE user_id = :uid"),
        {"uid": uid},
    ).scalar() or 0

    # Count applications
    app_count = db.execute(
        text("SELECT COUNT(*) FROM applications WHERE user_id = :uid"),
        {"uid": uid},
    ).scalar() or 0

    # Count pending approvals
    pending = db.execute(
        text("SELECT COUNT(*) FROM pending_approvals WHERE user_id = :uid AND status = 'pending'"),
        {"uid": uid},
    ).scalar() or 0

    # Count job matches
    match_count = db.execute(
        text("SELECT COUNT(*) FROM match_scores WHERE user_id = :uid"),
        {"uid": uid},
    ).scalar() or 0

    # Top matches
    top_matches = []
    try:
        rows = db.execute(
            text(
                "SELECT jp.id, jp.title, COALESCE(c.name, '') as company, ms.score "
                "FROM match_scores ms "
                "JOIN job_postings jp ON ms.job_posting_id = jp.id "
                "LEFT JOIN companies c ON jp.company_id = c.id "
                "WHERE ms.user_id = :uid ORDER BY ms.score DESC LIMIT 5"
            ),
            {"uid": uid},
        ).fetchall()
        for row in rows:
            top_matches.append({
                "id": str(row[0]),
                "title": row[1] or "Unknown",
                "company": row[2] or "",
                "location": "",
                "match_score": row[3] or 0,
            })
    except Exception:
        pass

    # Recent activity from process_statuses
    recent_activity = []
    try:
        rows = db.execute(
            text(
                "SELECT id, task_name, status, updated_at FROM process_statuses "
                "WHERE user_id = :uid ORDER BY updated_at DESC LIMIT 10"
            ),
            {"uid": uid},
        ).fetchall()
        for row in rows:
            recent_activity.append({
                "id": str(row[0]),
                "type": "job_found",
                "message": f"{row[1]} - {row[2]}",
                "timestamp": row[3].isoformat() if row[3] else datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass

    if not recent_activity:
        if resume_count > 0:
            recent_activity.append({
                "id": "activity-1",
                "type": "job_found",
                "message": f"You have {resume_count} resume(s) uploaded. Start the job discovery pipeline to find matching roles.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        else:
            recent_activity.append({
                "id": "activity-welcome",
                "type": "job_found",
                "message": "Welcome to CareerPilot! Upload your resume to get started.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    interview_rate = 0.0
    if app_count > 0:
        interview_count = db.execute(
            text("SELECT COUNT(*) FROM applications WHERE user_id = :uid AND status IN ('interview', 'offer')"),
            {"uid": uid},
        ).scalar() or 0
        interview_rate = round((interview_count / app_count) * 100, 1)

    # Scraper status — latest run and source breakdown
    total_linkedin = db.execute(
        text("SELECT COUNT(*) FROM job_postings WHERE source = 'linkedin'"),
    ).scalar() or 0
    total_naukri = db.execute(
        text("SELECT COUNT(*) FROM job_postings WHERE source = 'naukri'"),
    ).scalar() or 0
    total_manual = db.execute(
        text("SELECT COUNT(*) FROM job_postings WHERE source = 'manual'"),
    ).scalar() or 0

    last_scrape = db.execute(
        text("SELECT MAX(discovered_at) FROM job_postings"),
    ).scalar()
    last_scrape_iso = last_scrape.isoformat() if last_scrape else None

    return {
        "total_jobs_found": match_count,
        "total_applications_sent": app_count,
        "pending_approvals": pending,
        "interview_rate": interview_rate,
        "top_matches": top_matches,
        "recent_activity": recent_activity,
        "scraper": {
            "total_jobs": total_linkedin + total_naukri + total_manual,
            "source_breakdown": {
                "linkedin": total_linkedin,
                "naukri": total_naukri,
                "manual": total_manual,
            },
            "last_scrape_at": last_scrape_iso,
            "is_scraping": False,
        },
    }


@router.get("/analytics")
async def get_analytics(user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Return analytics data for the current user."""
    uid = user_id

    total_jobs = db.execute(
        text("SELECT COUNT(*) FROM match_scores WHERE user_id = :uid"),
        {"uid": uid},
    ).scalar() or 0

    total_apps = db.execute(
        text("SELECT COUNT(*) FROM applications WHERE user_id = :uid"),
        {"uid": uid},
    ).scalar() or 0

    approval_rate = 0.0
    interview_conversion = 0.0

    return {
        "match_trends": [],
        "source_breakdown": [
            {"source": "LinkedIn", "count": 0, "applications": 0},
            {"source": "Naukri", "count": 0, "applications": 0},
            {"source": "Indeed", "count": 0, "applications": 0},
        ],
        "funnel": [
            {"stage": "Jobs Discovered", "count": total_jobs},
            {"stage": "Matched", "count": total_jobs},
            {"stage": "Applied", "count": total_apps},
            {"stage": "Interview", "count": 0},
            {"stage": "Offer", "count": 0},
        ],
        "total_jobs": total_jobs,
        "total_applications": total_apps,
        "approval_rate": approval_rate,
        "interview_conversion": interview_conversion,
    }
