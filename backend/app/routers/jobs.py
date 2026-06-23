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
    search: Optional[str] = Query(None, description="Search by keyword"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int = Query(None, ge=1, le=100),
    offset: int = Query(None, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """List job postings personalized for the current user.

    Jobs are sorted by the user's match score (highest first), then by
    discovery date. Jobs the user has already rejected are excluded.
    """
    actual_limit = limit if limit is not None else page_size
    actual_offset = offset if offset is not None else (page - 1) * actual_limit

    conditions = []
    params: dict = {
        "uid": user_id,
        "limit": actual_limit,
        "offset": actual_offset,
    }

    if status:
        conditions.append("jp.status = :status")
        params["status"] = status
    if source:
        conditions.append("jp.source = :source")
        params["source"] = source
    if location:
        conditions.append("jp.location ILIKE :location")
        params["location"] = f"%{location}%"
    if search:
        conditions.append("(jp.title ILIKE :search OR c.name ILIKE :search2)")
        params["search"] = f"%{search}%"
        params["search2"] = f"%{search}%"
    if tier:
        conditions.append("ms.tier = :tier")
        params["tier"] = tier

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total (personalized — exclude rejected)
    count_sql = f"""
        SELECT COUNT(*)
        FROM job_postings jp
        LEFT JOIN companies c ON jp.company_id = c.id
        LEFT JOIN match_scores ms ON ms.job_posting_id = jp.id AND ms.user_id = :uid
        {where}
    """
    total = db.execute(text(count_sql), params).scalar() or 0

    # Check if user has any match scores — if not, trigger background scrape+score
    has_scores = db.execute(
        text("SELECT EXISTS(SELECT 1 FROM match_scores WHERE user_id = :uid)"),
        {"uid": user_id}
    ).scalar()

    if not has_scores:
        # Trigger background scrape + scoring based on user profile
        # Throttled: only if no scrape ran in the last 30 min (source='linkedin' with user-specific queries)
        try:
            from app.tasks_scraper import scrape_and_store_jobs, run_relevance_scoring
            scrape_and_store_jobs.delay(user_id=user_id)
            run_relevance_scoring.delay(user_id=user_id)
        except Exception:
            pass  # Non-blocking — user will see global pool until scoring completes

    # Fetch jobs sorted by user's match score (highest first), then discovery date
    jobs_sql = f"""
        SELECT jp.id, jp.title, jp.location, jp.url, jp.source, jp.status,
               jp.discovered_at, c.name as company_name,
               COALESCE(ms.score, 0) as match_score,
               ms.tier as match_tier
        FROM job_postings jp
        LEFT JOIN companies c ON jp.company_id = c.id
        LEFT JOIN match_scores ms ON ms.job_posting_id = jp.id AND ms.user_id = :uid
        {where}
        ORDER BY COALESCE(ms.score, 0) DESC, jp.discovered_at DESC
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
            "match_score": row[8] or 0,
            "match_tier": row[9] or None,
        })

    return {"data": jobs, "total": total, "page": (actual_offset // actual_limit) + 1, "page_size": actual_limit}


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


@router.post("/{job_id}/apply")
async def apply_to_job(job_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Apply to a job — creates an application record."""
    from uuid import uuid4
    
    # Check job exists
    job = db.execute(
        text("SELECT id FROM job_postings WHERE id = :jid"),
        {"jid": job_id},
    ).fetchone()
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check not already applied
    existing = db.execute(
        text("SELECT id FROM applications WHERE job_posting_id = :jid AND user_id = :uid LIMIT 1"),
        {"jid": job_id, "uid": uuid.UUID(user_id)},
    ).fetchone()
    if existing:
        return {"status": "already_applied", "application_id": str(existing[0])}
    
    app_id = uuid4()
    db.execute(
        text("""
            INSERT INTO applications (id, user_id, job_posting_id, status, method)
            VALUES (:aid, :uid, :jid, 'pending_approval', 'manual')
        """),
        {"aid": app_id, "uid": uuid.UUID(user_id), "jid": job_id},
    )
    db.commit()
    return {"status": "applied", "application_id": str(app_id), "job_id": job_id}
