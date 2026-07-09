"""
CareerPilot AI — Jobs API Router.
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
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

@router.get("")
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
        conditions.append("uj.status = :status")
        params["status"] = status
    if source:
        conditions.append("jp.source_platform = :source")
        params["source"] = source
    if location:
        conditions.append("jp.location ILIKE :location")
        params["location"] = f"%{location}%"
    if search:
        conditions.append("(jp.title ILIKE :search OR c.name ILIKE :search2 OR COALESCE(jp.description, '') ILIKE :search3)")
        params["search"] = f"%{search}%"
        params["search2"] = f"%{search}%"
        params["search3"] = f"%{search}%"
    if tier:
        conditions.append("ms.grade = :tier")
        params["tier"] = tier

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total (personalized — only jobs mapped to this user)
    count_sql = f"""
        SELECT COUNT(*)
        FROM job_postings jp
        INNER JOIN user_jobs uj ON uj.job_posting_id = jp.id AND uj.user_id = :uid
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
        try:
            from app.tasks_scraper import scrape_and_store_jobs, run_relevance_scoring
            loc_row = db.execute(
                text("SELECT preferred_location FROM user_profiles WHERE user_id = :uid"),
                {"uid": user_id}
            ).mappings().fetchone()
            scrape_location = loc_row.get("preferred_location") if loc_row else None
            scrape_and_store_jobs.delay(user_id=user_id, location=scrape_location)
            run_relevance_scoring.delay(user_id=user_id)
        except Exception:
            pass

    jobs_sql = f"""
        SELECT jp.id, jp.title, jp.location, jp.source_url, jp.source_platform,
               jp.posted_at, jp.created_at, jp.updated_at, jp.description,
               jp.salary_min, jp.salary_max, jp.currency, uj.status as user_status,
               c.name as company_name, COALESCE(ms.overall_score, 0) as match_score,
               ms.grade as match_tier, ms.details
        FROM job_postings jp
        INNER JOIN user_jobs uj ON uj.job_posting_id = jp.id AND uj.user_id = :uid
        LEFT JOIN companies c ON jp.company_id = c.id
        LEFT JOIN match_scores ms ON ms.job_posting_id = jp.id AND ms.user_id = :uid
        {where}
        ORDER BY COALESCE(ms.overall_score, 0) DESC, jp.posted_at DESC
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
            "posted_at": row[5].isoformat() if row[5] else None,
            "created_at": row[6].isoformat() if row[6] else None,
            "updated_at": row[7].isoformat() if row[7] else None,
            "description": row[8] or "",
            "salary_min": float(row[9]) if row[9] is not None else None,
            "salary_max": float(row[10]) if row[10] is not None else None,
            "salary_currency": row[11] or "USD",
            "status": row[12] or "new",
            "company": row[13] or "Unknown",
            "match_score": int(row[14] or 0),
            "tier": row[15] or "tier_c",
            "match_tier": row[15] or None,
            "match_breakdown": (row[16] or {}).get("breakdown") if isinstance(row[16], dict) else None,
        })

    return {"data": jobs, "total": total, "page": (actual_offset // actual_limit) + 1, "page_size": actual_limit}

# ---------------------------------------------------------------------------
# New scrape‑status endpoint (exposed under /jobs/scrape-status)
# ---------------------------------------------------------------------------
@router.get("/scrape-status", tags=["jobs"])
async def scrape_status(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Return latest scrape job counts.

    - total_jobs: all jobs with status='new'
    - linkedin_jobs: jobs sourced from LinkedIn
    - naukri_jobs: jobs sourced from Naukri
    - matched_jobs: number of jobs already scored for this user
    """
    total = db.execute(text("SELECT COUNT(*) FROM job_postings WHERE status = 'new'")).scalar()
    linkedin = db.execute(text("SELECT COUNT(*) FROM job_postings WHERE source = 'linkedin'")).scalar()
    naukri = db.execute(text("SELECT COUNT(*) FROM job_postings WHERE source = 'naukri'")).scalar()
    matched = db.execute(
        text("SELECT COUNT(*) FROM match_scores WHERE user_id = :uid"),
        {"uid": uuid.UUID(user_id)},
    ).scalar()
    return {
        "total_jobs": total,
        "linkedin_jobs": linkedin,
        "naukri_jobs": naukri,
        "matched_jobs": matched,
    }

# ---------------------------------------------------------------------------
# Job detail endpoints – must appear after static routes like /scrape-status
# ---------------------------------------------------------------------------
@router.get("/{job_id}")
async def get_job(job_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Get a specific job posting with match details (only if mapped to this user)."""
    try:
        uuid.UUID(str(job_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Job not found")

    row = db.execute(
        text("""
            SELECT jp.id, jp.title, jp.description, jp.location, jp.source_url, jp.source_platform,
                   jp.salary_min, jp.salary_max, jp.currency, jp.posted_at, jp.created_at, jp.updated_at,
                   c.name as company_name, uj.status
            FROM job_postings jp
            INNER JOIN user_jobs uj ON uj.job_posting_id = jp.id AND uj.user_id = :uid
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE jp.id = :jid
        """),
        {"jid": job_id, "uid": user_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    match = db.execute(
        text("""
            SELECT id, overall_score, grade, details
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
        "salary_currency": row[8] or "USD",
        "posted_at": row[9].isoformat() if row[9] else None,
        "created_at": row[10].isoformat() if row[10] else None,
        "updated_at": row[11].isoformat() if row[11] else None,
        "company": row[12] or "Unknown",
        "status": row[13] or "new",
    }

    if match:
        result["match"] = {
            "id": str(match[0]),
            "score": match[1],
            "tier": match[2],
            "details": match[3],
        }
        result["match_score"] = int(match[1] or 0)
        result["tier"] = match[2] or "tier_c"
        details = match[3] if isinstance(match[3], dict) else {}
        result["match_breakdown"] = details.get("breakdown") or {
            "skills": int(details.get("skills_score", 0) or 0),
            "experience": int(details.get("experience_score", 0) or 0),
            "education": int(details.get("education_score", 0) or 0),
            "location": int(details.get("location_score", 0) or 0),
            "salary": int(details.get("salary_score", 0) or 0),
            "overall": int(match[1] or 0),
        }
    else:
        result["match_score"] = 0
        result["tier"] = "tier_c"

    return result

@router.post("/{job_id}/save")
async def save_job(job_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Save a job to user's saved list."""
    db.execute(
        text("INSERT INTO user_jobs (user_id, job_posting_id, status) VALUES (:uid, :jid, 'saved') ON CONFLICT (user_id, job_posting_id) DO UPDATE SET status = 'saved'"),
        {"uid": user_id, "jid": job_id},
    )
    db.commit()
    return {"status": "saved", "job_id": job_id}

@router.post("/{job_id}/reject")
async def reject_job(job_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Reject a job (hide from results)."""
    db.execute(
        text("INSERT INTO user_jobs (user_id, job_posting_id, status) VALUES (:uid, :jid, 'rejected') ON CONFLICT (user_id, job_posting_id) DO UPDATE SET status = 'rejected'"),
        {"uid": user_id, "jid": job_id},
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
            INSERT INTO applications (id, user_id, job_posting_id, status)
            VALUES (:aid, :uid, :jid, 'SUBMITTED')
        """),
        {"aid": app_id, "uid": uuid.UUID(user_id), "jid": job_id},
    )
    db.commit()
    return {"status": "applied", "application_id": str(app_id), "job_id": job_id}
