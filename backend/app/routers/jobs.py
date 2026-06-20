"""
CareerPilot AI — Jobs API Router.

Endpoints for browsing discovered job postings with filtering.
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from ..auth import get_current_user_id

router = APIRouter(prefix="/jobs", tags=["jobs"])


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


@router.get("/")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    tier: Optional[str] = Query(None, description="Filter by match tier"),
    source: Optional[str] = Query(None, description="Filter by source"),
    location: Optional[str] = Query(None, description="Filter by location"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """List job postings with optional filters."""
    # Build query dynamically
    conditions = []
    params = {"limit": limit, "offset": offset}

    if status:
        conditions.append("jp.status = :status")
        params["status"] = status
    if source:
        conditions.append("jp.source = :source")
        params["source"] = source
    if location:
        conditions.append("jp.location ILIKE :location")
        params["location"] = f"%{location}%"

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_sql = f"SELECT COUNT(*) FROM job_postings jp {where}"
    total = db.execute(text(count_sql), params).scalar() or 0

    # Fetch jobs
    jobs_sql = f"""
        SELECT jp.id, jp.title, jp.location, jp.url, jp.source, jp.status,
               jp.discovered_at, c.name as company_name
        FROM job_postings jp
        LEFT JOIN companies c ON jp.company_id = c.id
        {where}
        ORDER BY jp.discovered_at DESC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(jobs_sql), params).fetchall()

    jobs = []
    for row in rows:
        jobs.append({
            "id": str(row[0]),
            "title": row[1],
            "location": row[2],
            "url": row[3],
            "source": row[4],
            "status": row[5],
            "discovered_at": row[6].isoformat() if row[6] else None,
            "company": row[7] or "Unknown",
        })

    return {"jobs": jobs, "total": total, "limit": limit, "offset": offset}


@router.get("/{job_id}")
async def get_job(job_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Get a specific job posting with match details."""
    row = db.execute(
        text("""
            SELECT jp.id, jp.title, jp.description, jp.location, jp.url, jp.source,
                   jp.salary_min, jp.salary_max, jp.posted_at, jp.discovered_at,
                   jp.status, c.name as company_name
            FROM job_postings jp
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE jp.id = :jid
        """),
        {"jid": job_id},
    ).fetchone()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    # Get match score for this user
    match = db.execute(
        text("""
            SELECT id, score, tier, reasons_json, missing_skills_json
            FROM match_scores
            WHERE job_posting_id = :jid AND user_id = :uid
            LIMIT 1
        """),
        {"jid": job_id, "uid": uuid.UUID(user_id)},
    ).fetchone()

    result = {
        "id": str(row[0]),
        "title": row[1],
        "description": row[2],
        "location": row[3],
        "url": row[4],
        "source": row[5],
        "salary_min": row[6],
        "salary_max": row[7],
        "posted_at": row[8].isoformat() if row[8] else None,
        "discovered_at": row[9].isoformat() if row[9] else None,
        "status": row[10],
        "company": row[11] or "Unknown",
    }

    if match:
        result["match"] = {
            "id": str(match[0]),
            "score": match[1],
            "tier": match[2],
            "reasons": match[3],
            "missing_skills": match[4],
        }

    return result


@router.post("/{job_id}/save")
async def save_job(job_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Save a job to user's saved list."""
    db.execute(
        text("UPDATE job_postings SET status = 'saved' WHERE id = :jid"),
        {"jid": job_id},
    )
    db.commit()
    return {"status": "saved", "job_id": job_id}


@router.post("/{job_id}/reject")
async def reject_job(job_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Reject a job (hide from results)."""
    db.execute(
        text("UPDATE job_postings SET status = 'rejected' WHERE id = :jid"),
        {"jid": job_id},
    )
    db.commit()
    return {"status": "rejected", "job_id": job_id}
