"""
CareerPilot AI — Scraper Celery Tasks
=======================================
Celery tasks for automated job scraping and relevance scoring.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from celery import current_app as celery_app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _get_db():
    """Create a SQLAlchemy session."""
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    return Session(engine), engine


# ---------------------------------------------------------------------------
# Job Scraping Task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    name="app.tasks_scraper.scrape_and_store_jobs",
    time_limit=600,
    soft_time_limit=540,
)
def scrape_and_store_jobs(self, user_id: str | None = None) -> dict:
    """Scrape jobs from all portals and store in PostgreSQL.

    Args:
        user_id: Optional user ID to customize queries (uses default if None).

    Returns:
        Dict with counts: total, linkedin, naukri, new_stored.
    """
    logger.info("scrape_and_store_jobs started (user_id=%s)", user_id)

    try:
        from app.agents.multi_portal_scraper import scrape_all
        import asyncio

        # Default queries (can be customized per user later)
        linkedin_queries = [
            "software engineer", "network engineer", "infrastructure engineer",
            "cybersecurity analyst", "SOC analyst", "cloud engineer",
            "devops engineer", "system administrator",
        ]
        naukri_queries = [
            "software engineer", "network engineer", "infrastructure engineer",
            "cybersecurity", "cloud engineer", "devops",
            "system administrator", "Windows administrator",
        ]

        result = asyncio.run(scrape_all(
            linkedin_queries=linkedin_queries,
            naukri_queries=naukri_queries,
            location="India",
        ))

        jobs = result["jobs"]
        summary = result["summary"]

        # Store in PostgreSQL
        session, engine = _get_db()
        new_count = 0
        try:
            for job in jobs:
                # Check if job already exists by hash_key
                existing = session.execute(
                    text("SELECT id FROM job_postings WHERE hash_key = :hk"),
                    {"hk": job.get("hash_key", "")},
                ).fetchone()

                if existing:
                    continue

                # Insert new job posting
                session.execute(
                    text(
                        """
                        INSERT INTO job_postings
                            (title, location, description, url, source,
                             hash_key, status, discovered_at)
                        VALUES
                            (:title, :location, :desc, :url, :source,
                             :hk, 'new', NOW())
                        """
                    ),
                    {
                        "title": job.get("title", ""),
                        "location": job.get("location", ""),
                        "desc": job.get("description", "")[:5000],
                        "url": job.get("url", ""),
                        "source": job.get("source", ""),
                        "hk": job.get("hash_key", ""),
                    },
                )
                new_count += 1

            session.commit()
        finally:
            session.close()
            engine.dispose()

        logger.info(
            "scrape_and_store_jobs completed: %d total, %d new stored",
            summary["total_jobs"], new_count,
        )

        return {
            "total_scraped": summary["total_jobs"],
            "linkedin": summary["linkedin_jobs"],
            "naukri": summary["naukri_jobs"],
            "new_stored": new_count,
            "elapsed_seconds": summary["elapsed_seconds"],
        }

    except Exception as exc:
        logger.exception("scrape_and_store_jobs failed")
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Relevance Scoring Task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
    name="app.tasks_scraper.run_relevance_scoring",
    time_limit=300,
    soft_time_limit=240,
)
def run_relevance_scoring(self, user_id: str) -> dict:
    """Score all unscraped jobs against a user's profile.

    Args:
        user_id: UUID of the user to score jobs for.

    Returns:
        Dict with count of scored jobs.
    """
    logger.info("run_relevance_scoring started (user_id=%s)", user_id)

    try:
        from app.agents.job_relevance import UserProfile, score_job

        session, engine = _get_db()
        try:
            # Load user profile
            profile_row = session.execute(
                text(
                    "SELECT full_name, skills, experience, summary, "
                    "preferred_location, target_roles, total_years_experience "
                    "FROM user_profiles WHERE user_id = :uid"
                ),
                {"uid": user_id},
            ).mappings().fetchone()

            if not profile_row:
                logger.warning("No profile found for user %s", user_id)
                return {"scored": 0, "reason": "no_profile"}

            # Build UserProfile
            skills = []
            if profile_row.get("skills"):
                s = profile_row["skills"]
                if isinstance(s, str):
                    import json as _json
                    s = _json.loads(s)
                if isinstance(s, list):
                    skills = s
                elif isinstance(s, dict):
                    for v in s.values():
                        if isinstance(v, list):
                            skills.extend(v)
                        elif isinstance(v, str):
                            skills.append(v)

            target_roles = []
            if profile_row.get("target_roles"):
                r = profile_row["target_roles"]
                if isinstance(r, str):
                    import json as _json
                    r = _json.loads(r)
                if isinstance(r, list):
                    target_roles = r

            preferred_locs = []
            if profile_row.get("preferred_location"):
                preferred_locs = [profile_row["preferred_location"]]

            exp_years = float(profile_row.get("total_years_experience", 0) or 0)

            profile = UserProfile(
                full_name=profile_row.get("full_name", ""),
                skills=skills,
                experience_years=exp_years,
                preferred_locations=preferred_locs,
                target_roles=target_roles,
                summary=profile_row.get("summary", ""),
            )

            # Load unscored jobs
            jobs = session.execute(
                text(
                    "SELECT jp.id, jp.title, jp.location, jp.description, "
                    "jp.source, jp.url "
                    "FROM job_postings jp "
                    "LEFT JOIN match_scores ms ON ms.job_posting_id = jp.id AND ms.user_id = :uid "
                    "WHERE ms.id IS NULL AND jp.status = 'new' "
                    "ORDER BY jp.discovered_at DESC "
                    "LIMIT 200"
                ),
                {"uid": user_id},
            ).mappings().all()

            scored = 0
            for job in jobs:
                job_dict = {
                    "title": job.get("title", ""),
                    "location": job.get("location", ""),
                    "description": job.get("description", ""),
                    "employment_type": "",
                    "source": job.get("source", ""),
                    "url": job.get("url", ""),
                }

                relevance = score_job(profile, job_dict)

                session.execute(
                    text(
                        """
                        INSERT INTO match_scores
                            (user_id, job_posting_id, score, tier, reasons_json,
                             missing_skills_json, risk_indicators_json)
                        VALUES
                            (:uid, :jid, :score, :tier, :reasons,
                             :missing, :risk)
                        ON CONFLICT (user_id, job_posting_id) DO UPDATE SET
                            score = EXCLUDED.score,
                            tier = EXCLUDED.tier,
                            reasons_json = EXCLUDED.reasons_json
                        """
                    ),
                    {
                        "uid": user_id,
                        "jid": str(job["id"]),
                        "score": int(round(relevance.get("total_score", 0))),
                        "tier": _tier_from_score(relevance.get("total_score", 0)),
                        "reasons": json.dumps(relevance, ensure_ascii=False),
                        "missing": json.dumps(relevance.get("missing_skills", []), ensure_ascii=False),
                        "risk": json.dumps(relevance.get("risk_indicators", []), ensure_ascii=False),
                    },
                )
                scored += 1

            session.commit()
        finally:
            session.close()
            engine.dispose()

        logger.info("run_relevance_scoring completed: %d jobs scored", scored)
        return {"scored": scored}

    except Exception as exc:
        logger.exception("run_relevance_scoring failed")
        raise self.retry(exc=exc)


def _tier_from_score(score: float) -> str:
    """Convert numeric score to tier."""
    if score >= 80:
        return "excellent"
    elif score >= 60:
        return "good"
    elif score >= 40:
        return "fair"
    else:
        return "poor"
