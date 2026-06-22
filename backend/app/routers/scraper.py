"""
CareerPilot AI — Scraper API Router
=====================================
FastAPI endpoints for job scraping, relevance scoring, and cover letters.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    return Session(engine), engine


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class TriggerScrapeRequest(BaseModel):
    linkedin_queries: Optional[list[str]] = None
    naukri_queries: Optional[list[str]] = None
    location: Optional[str] = None  # None = use user's preferred_location from profile

    class Config:
        # Allow empty body
        extra = "forbid"


class ScrapeStatusResponse(BaseModel):
    total_scraped: int
    linkedin: int
    naukri: int
    new_stored: int
    elapsed_seconds: float


class JobMatchResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str
    source: str
    url: str
    relevance_score: float
    skills_score: float
    experience_score: float
    grade: str
    matched_skills: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/scraper/trigger", tags=["scraper"])
async def trigger_scrape(
    request: TriggerScrapeRequest = Body(default=None),
    user_id: str = Depends(get_current_user_id),
):
    """Trigger a manual job scrape.

    If custom queries (linkedin_queries / naukri_queries) are provided they
    are used; otherwise the task builds queries from the user's profile.
    After scraping completes, relevance scoring is triggered automatically.
    """
    from app.tasks_scraper import scrape_and_store_jobs

    # If the user supplied custom queries, pass them through via kwargs
    kwargs: dict = {"user_id": user_id}
    if request is not None:
        if request.linkedin_queries:
            kwargs["linkedin_queries"] = request.linkedin_queries
        if request.naukri_queries:
            kwargs["naukri_queries"] = request.naukri_queries
        if request.location:
            kwargs["location"] = request.location

    task = scrape_and_store_jobs.delay(**kwargs)
    return {"task_id": task.id, "status": "started"}


@router.get("/scraper/status", tags=["scraper"])
async def scrape_status(
    user_id: str = Depends(get_current_user_id),
):
    """Get latest scrape results and job counts."""
    session, engine = _get_db()
    try:
        total = session.execute(
            text("SELECT COUNT(*) FROM job_postings WHERE status = 'new'")
        ).scalar()

        linkedin_count = session.execute(
            text("SELECT COUNT(*) FROM job_postings WHERE source = 'linkedin'")
        ).scalar()

        naukri_count = session.execute(
            text("SELECT COUNT(*) FROM job_postings WHERE source = 'naukri'")
        ).scalar()

        matched_count = session.execute(
            text("SELECT COUNT(*) FROM match_scores WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()

        return {
            "total_jobs": total,
            "linkedin_jobs": linkedin_count,
            "naukri_jobs": naukri_count,
            "matched_jobs": matched_count,
        }
    finally:
        session.close()
        engine.dispose()


@router.get("/jobs/matches", tags=["jobs"])
async def get_matches(
    min_score: float = Query(35.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    source: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    """Get relevance-scored job matches for the current user."""
    session, engine = _get_db()
    try:
        query = """
            SELECT
                jp.id, jp.title, jp.location, jp.source,
                jp.url,
                ms.score, ms.tier, ms.reasons_json,
                ms.missing_skills_json
            FROM match_scores ms
            JOIN job_postings jp ON jp.id = ms.job_posting_id
            WHERE ms.user_id = :uid AND ms.score >= :min_score
        """
        params: dict[str, Any] = {"uid": user_id, "min_score": int(min_score)}

        if source:
            query += " AND jp.source = :source"
            params["source"] = source

        query += " ORDER BY ms.score DESC LIMIT :limit"
        params["limit"] = limit

        rows = session.execute(text(query), params).mappings().all()

        results = []
        for row in rows:
            reasons = {}
            if row.get("reasons_json"):
                d = row["reasons_json"]
                if isinstance(d, str):
                    import json as _json
                    d = _json.loads(d)
                if isinstance(d, dict):
                    reasons = d

            missing_skills = []
            if row.get("missing_skills_json"):
                d = row["missing_skills_json"]
                if isinstance(d, str):
                    import json as _json
                    d = _json.loads(d)
                if isinstance(d, list):
                    missing_skills = d

            results.append({
                "id": str(row["id"]),
                "title": row.get("title", ""),
                "company": "",
                "location": row.get("location", ""),
                "source": row.get("source", ""),
                "url": row.get("url", ""),
                "relevance_score": row.get("score", 0),
                "tier": row.get("tier", ""),
                "matched_skills": reasons.get("matched_skills", []),
                "missing_skills": missing_skills,
            })

        return {"matches": results, "count": len(results)}
    finally:
        session.close()
        engine.dispose()


@router.post("/jobs/{job_id}/generate-cover-letter", tags=["jobs"])
async def generate_cover_letter(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a cover letter for a specific job."""
    from app.agents.cover_letter_generator import generate_cover_letter

    session, engine = _get_db()
    try:
        # Load job with company name
        job = session.execute(
            text(
                "SELECT jp.*, c.name as company_name "
                "FROM job_postings jp "
                "LEFT JOIN companies c ON jp.company_id = c.id "
                "WHERE jp.id = :jid"
            ),
            {"jid": job_id},
        ).mappings().fetchone()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Load user profile
        profile_row = session.execute(
            text(
                "SELECT full_name, skills, experience, summary, "
                "preferred_location, target_roles "
                "FROM user_profiles WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).mappings().fetchone()

        if not profile_row:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Build profile dict
        import json as _json

        skills = []
        if profile_row.get("skills"):
            s = profile_row["skills"]
            if isinstance(s, str):
                s = _json.loads(s)
            if isinstance(s, list):
                skills = s
            elif isinstance(s, dict):
                for v in s.values():
                    if isinstance(v, list):
                        skills.extend(v)

        target_roles = []
        if profile_row.get("target_roles"):
            r = profile_row["target_roles"]
            if isinstance(r, str):
                r = _json.loads(r)
            if isinstance(r, list):
                target_roles = r

        exp_years = 0.0
        if profile_row.get("experience"):
            e = profile_row["experience"]
            if isinstance(e, str):
                e = _json.loads(e)
            if isinstance(e, list):
                for item in e:
                    if isinstance(item, dict):
                        yrs = item.get("years", 0)
                        if yrs:
                            exp_years = max(exp_years, float(yrs))

        profile = {
            "full_name": profile_row.get("full_name", ""),
            "skills": skills,
            "experience_years": exp_years,
            "summary": profile_row.get("summary", ""),
            "target_roles": target_roles,
            "preferred_locations": [profile_row["preferred_location"]] if profile_row.get("preferred_location") else [],
        }

        job_dict = {
            "title": job.get("title", ""),
            "company": job.get("company_name") or job.get("company_name", ""),
            "location": job.get("location", ""),
            "description": job.get("description", "") or "",
            "skills": [],
            "experience_required": job.get("experience_required", "") or "",
            "employment_type": job.get("employment_type", "") or "",
        }

        letter = generate_cover_letter(profile, job_dict)

        # Store in DB
        try:
            session.execute(
                text(
                    """
                    INSERT INTO cover_letters
                        (user_id, job_posting_id, content)
                    VALUES
                        (:uid, :jid, :content)
                    """
                ),
                {
                    "uid": user_id,
                    "jid": job_id,
                    "content": letter,
                },
            )
            session.commit()
        except Exception:
            session.rollback()
            pass  # Non-critical, already have the letter

        return {
            "cover_letter": letter,
            "word_count": len(letter.split()),
            "job_title": job_dict["title"],
        }
    finally:
        session.close()
        engine.dispose()


@router.post("/scraper/score-jobs", tags=["scraper"])
async def trigger_scoring(
    user_id: str = Depends(get_current_user_id),
):
    """Trigger relevance scoring for the current user."""
    from app.tasks_scraper import run_relevance_scoring

    task = run_relevance_scoring.delay(user_id=user_id)
    return {"task_id": task.id, "status": "scoring_started"}
