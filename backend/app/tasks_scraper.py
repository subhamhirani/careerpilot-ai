"""
CareerPilot AI — Scraper Celery Tasks
=======================================
Celery tasks for automated job scraping and relevance scoring.
"""

from __future__ import annotations

import json
import logging
import os
import re
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
# Helpers
# ---------------------------------------------------------------------------

def _get_user_job_criteria(user_id: str | None) -> tuple[str | None, list[str]]:
    """Get user's first job title (primary role) and list of skills."""
    if not user_id:
        return None, []

    session, engine = _get_db()
    try:
        profile_row = session.execute(
            text(
                "SELECT preferred_roles, skills, headline FROM user_profiles WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).mappings().fetchone()

        if not profile_row:
            return None, []

        skills = []
        if profile_row.get("skills"):
            s = profile_row["skills"]
            if isinstance(s, str):
                s = json.loads(s)
            if isinstance(s, list):
                skills = [str(x).strip() for x in s if str(x).strip()]
            elif isinstance(s, dict):
                for v in s.values():
                    if isinstance(v, list):
                        skills.extend(str(x).strip() for x in v if str(x).strip())

        preferred_roles = []
        if profile_row.get("preferred_roles"):
            r = profile_row["preferred_roles"]
            if isinstance(r, str):
                r = json.loads(r)
            if isinstance(r, list):
                preferred_roles = [str(x).strip() for x in r if str(x).strip()]

        first_job_title = None
        if preferred_roles:
            first_job_title = preferred_roles[0]
        elif profile_row.get("headline"):
            first_job_title = str(profile_row["headline"]).strip()

        return first_job_title, skills
    except Exception as exc:
        logger.warning("Failed to fetch job criteria for user %s: %s", user_id, exc)
        return None, []
    finally:
        session.close()
        engine.dispose()


def _build_user_queries(user_id: str | None) -> tuple[list[str], list[str]]:
    """Build search queries based on first job title and then skills based.

    Falls back to sensible defaults if no profile is found.
    """
    default_linkedin = [
        "software engineer", "network engineer", "infrastructure engineer",
        "cybersecurity analyst", "SOC analyst", "cloud engineer",
        "devops engineer", "system administrator",
    ]
    default_naukri = [
        "software engineer", "network engineer", "infrastructure engineer",
        "cybersecurity", "cloud engineer", "devops",
        "system administrator", "Windows administrator",
    ]

    if not user_id:
        return default_linkedin, default_naukri

    first_job_title, skills = _get_user_job_criteria(user_id)
    if not first_job_title and not skills:
        return default_linkedin, default_naukri

    queries = []
    # 1. First job title alone
    if first_job_title:
        queries.append(first_job_title)
        # 2. First job title + skills based queries
        for skill in skills[:8]:
            q = f"{first_job_title} {skill}".strip()
            if q not in queries:
                queries.append(q)
    else:
        queries = skills[:8]

    queries = queries[:10]
    if not queries:
        return default_linkedin, default_naukri

    logger.info(
        "Built %d queries based on first job title '%s' and skills for user %s",
        len(queries),
        first_job_title,
        user_id,
    )
    return queries, queries


def _matches_user_criteria(job: dict, first_job_title: str | None, skills: list[str]) -> bool:
    """Filter scraped jobs so only jobs matching first job title and skills are kept."""
    if not first_job_title and not skills:
        return True

    title = str(job.get("title") or "").lower().strip()
    description = str(job.get("description") or "").lower().strip()
    job_skills_raw = job.get("skills") or []
    if isinstance(job_skills_raw, list):
        job_skills = " ".join(str(s) for s in job_skills_raw).lower()
    else:
        job_skills = str(job_skills_raw).lower()

    combined_text = f"{title} {description} {job_skills}"

    # 1. First job title check: title must match at least one core token of first_job_title
    if first_job_title:
        stopwords = {
            "senior", "junior", "lead", "staff", "principal", "associate",
            "intern", "and", "or", "for", "the", "in", "with", "of", "to",
            "at", "level", "i", "ii", "iii", "iv",
        }
        tokens = [w for w in re.findall(r"[a-z0-9+#]+", first_job_title.lower()) if len(w) >= 2 and w not in stopwords]
        if tokens:
            title_matched = any(token in title for token in tokens)
            if not title_matched:
                return False

    # 2. Skills check: must match at least one user skill if defined
    if skills:
        skill_matched = any(
            str(skill).lower().strip() in combined_text
            for skill in skills
            if str(skill).strip()
        )
        if not skill_matched:
            return False

    return True


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
def scrape_and_store_jobs(
    self,
    user_id: str | None = None,
    linkedin_queries: list[str] | None = None,
    naukri_queries: list[str] | None = None,
    location: str | None = None,
    selected_locations: list[str] | None = None,
) -> dict:
    """Scrape jobs from all portals and store in PostgreSQL.

    "selected_locations" overrides the generic location and defines priority locations to scrape.
    """
    """Scrape jobs from all portals and store in PostgreSQL.

    Args:
        user_id: Optional user ID to customize queries from profile.
        linkedin_queries: Optional custom LinkedIn search queries.
        naukri_queries: Optional custom Naukri search queries.
        location: Optional location override. If not provided, uses the
                  user's preferred_location from profile, or "India".

    Returns:
        Dict with counts: total, linkedin, naukri, new_stored.
    """
    logger.info("scrape_and_store_jobs started (user_id=%s, location=%s)", user_id, location)

    if user_id is None:
        logger.info("Scheduled scrape_and_store_jobs running across all active users")
        s, e = _get_db()
        try:
            users = s.execute(
                text("SELECT id FROM users WHERE is_active = true")
            ).mappings().fetchall()
            user_ids = [str(u["id"]) for u in users]
        except Exception as err:
            logger.warning("Could not fetch active users for scheduled scrape: %s", err)
            user_ids = []
        finally:
            s.close()
            e.dispose()

        if not user_ids:
            logger.info("No active users found for scheduled scrape")
            return {"total_scraped": 0, "new_stored": 0, "users_processed": 0}

        total_scraped = 0
        total_new = 0
        for uid in user_ids:
            try:
                res = scrape_and_store_jobs(
                    self,
                    user_id=uid,
                    linkedin_queries=linkedin_queries,
                    naukri_queries=naukri_queries,
                    location=location,
                    selected_locations=selected_locations,
                )
                total_scraped += res.get("total_scraped", 0)
                total_new += res.get("new_stored", 0)
            except Exception as exc:
                logger.warning("Scheduled scrape failed for user %s: %s", uid, exc)
        return {
            "total_scraped": total_scraped,
            "new_stored": total_new,
            "users_processed": len(user_ids),
        }

    try:
        from app.agents.multi_portal_scraper import scrape_all
        import asyncio

        # Resolve location: explicit param -> user profile -> default "India"
        resolved_location = location
        if not resolved_location and user_id:
            try:
                s, e = _get_db()
                row = s.execute(
                    text("SELECT preferred_location FROM user_profiles WHERE user_id = :uid"),
                    {"uid": user_id},
                ).mappings().fetchone()
                if row and row.get("preferred_location"):
                    resolved_location = row["preferred_location"]
                s.close()
                e.dispose()
            except Exception:
                pass
        if not resolved_location:
            resolved_location = "India"

        first_job_title, skills = _get_user_job_criteria(user_id)

        # Use custom queries if provided, otherwise build from user profile
        if linkedin_queries or naukri_queries:
            li_q = linkedin_queries or []
            na_q = naukri_queries or li_q
        else:
            li_q, na_q = _build_user_queries(user_id)

        result = asyncio.run(scrape_all(
            linkedin_queries=li_q,
            naukri_queries=na_q,
            location=resolved_location,
            selected_locations=selected_locations,
        ))

        jobs = result["jobs"]
        summary = result["summary"]

        # Filter scraped jobs so we only store jobs matching first job title and skills
        filtered_jobs = [
            j for j in jobs
            if _matches_user_criteria(j, first_job_title, skills)
        ]
        logger.info(
            "Filtered scraped jobs for user %s: kept %d / %d based on first job title '%s' and skills",
            user_id, len(filtered_jobs), len(jobs), first_job_title,
        )
        jobs = filtered_jobs

        # Store in PostgreSQL
        session, engine = _get_db()
        new_count = 0
        try:
            for job in jobs:
                # Get or create company
                company_name = job.get("company", "").strip() or "Unknown"
                company_row = session.execute(
                    text("SELECT id FROM companies WHERE name = :name"),
                    {"name": company_name},
                ).mappings().fetchone()
                if company_row:
                    company_id = company_row["id"]
                else:
                    # Create unknown companies lazily (only on first encounter)
                    if company_name == "Unknown":
                        # Try to find any existing "Unknown" company
                        existing = session.execute(
                            text("SELECT id FROM companies WHERE name = 'Unknown'"),
                        ).mappings().fetchone()
                        if existing:
                            company_id = existing["id"]
                        else:
                            company_id = session.execute(
                                text("INSERT INTO companies (name) VALUES ('Unknown') RETURNING id"),
                            ).scalar()
                    else:
                        company_id = session.execute(
                            text("INSERT INTO companies (name) VALUES (:name) RETURNING id"),
                            {"name": company_name},
                        ).scalar()

                job_hash = (job.get("hash_key") or "").strip() or None
                result = session.execute(
                    text(
                        """
                        INSERT INTO job_postings
                            (company_id, title, description, location,
                             source_url, source_platform, external_id,
                             hash_key, status, is_active)
                        VALUES
                            (:cid, :title, :desc, :location,
                             :url, :source, :source_job_id,
                             :hk, 'new', true)
                        ON CONFLICT (hash_key) WHERE hash_key IS NOT NULL DO NOTHING
                        RETURNING id
                        """
                    ),
                    {
                        "cid": company_id,
                        "title": job.get("title", ""),
                        "desc": job.get("description", "")[:5000],
                        "location": job.get("location", ""),
                        "url": job.get("url", ""),
                        "source": job.get("source", ""),
                        "source_job_id": job.get("source_job_id", ""),
                        "hk": job_hash,
                    },
                )
                job_id = result.scalar()
                if job_id:
                    new_count += 1
                elif job_hash:
                    existing_job = session.execute(
                        text("SELECT id FROM job_postings WHERE hash_key = :hk"),
                        {"hk": job_hash},
                    ).mappings().fetchone()
                    job_id = existing_job["id"] if existing_job else None

                # Map both newly inserted and already-existing jobs to the user.
                if user_id and job_id:
                    session.execute(
                        text(
                            """
                            INSERT INTO user_jobs (user_id, job_posting_id, status)
                            VALUES (:uid, :jid, 'new')
                            ON CONFLICT (user_id, job_posting_id) DO NOTHING
                            """
                        ),
                        {"uid": user_id, "jid": job_id},
                    )

            session.commit()
        finally:
            session.close()
            engine.dispose()

        logger.info(
            "scrape_and_store_jobs completed: %d total, %d new stored",
            summary["total_jobs"], new_count,
        )

        # Auto-trigger relevance scoring for the user
        if user_id and new_count > 0:
            try:
                from app.tasks_scraper import run_relevance_scoring
                score_task = run_relevance_scoring.delay(user_id=user_id)
                logger.info(
                    "Auto-triggered scoring for user %s after scrape: task %s",
                    user_id, score_task.id,
                )
            except Exception as score_err:
                logger.warning("Auto-trigger scoring failed: %s", score_err)

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

    Supports two scoring modes controlled by the ``SCORING_METHOD``
    environment variable (default: ``heuristic``):

      * ``heuristic``  — keyword/skill-based scoring (``job_relevance.score_job``)
      * ``multi_agent`` — three-agent pipeline with embeddings, web research,
                          and LLM synthesis (``multi_agent_scoring.MultiAgentScorer``)

    Args:
        user_id: UUID of the user to score jobs for.

    Returns:
        Dict with count of scored jobs.
    """
    logger.info("run_relevance_scoring started (user_id=%s)", user_id)

    try:
        from app.agents.job_relevance import UserProfile, score_job

        scoring_method = os.getenv("SCORING_METHOD", "heuristic").strip().lower()
        session, engine = _get_db()
        try:
            # ── Load user profile ──────────────────────────────────
            profile_row = session.execute(
                text(
                    "SELECT full_name, headline, skills, experience, summary, "
                    "preferred_location, preferred_roles "
                    "FROM user_profiles WHERE user_id = :uid"
                ),
                {"uid": user_id},
            ).mappings().fetchone()

            if not profile_row:
                logger.warning("No profile found for user %s", user_id)
                return {"scored": 0, "reason": "no_profile"}

            # Build UserProfile (heuristic path) + profile_dict (multi-agent path)
            skills: list[str] = []
            raw_skills = profile_row.get("skills")
            if raw_skills:
                if isinstance(raw_skills, str):
                    import json as _j
                    raw_skills = _j.loads(raw_skills)
                if isinstance(raw_skills, list):
                    skills = raw_skills
                elif isinstance(raw_skills, dict):
                    for v in raw_skills.values():
                        if isinstance(v, list):
                            skills.extend(v)
                        elif isinstance(v, str):
                            skills.append(v)

            preferred_roles: list[str] = []
            raw_roles = profile_row.get("preferred_roles")
            if raw_roles:
                if isinstance(raw_roles, str):
                    import json as _j
                    raw_roles = _j.loads(raw_roles)
                if isinstance(raw_roles, list):
                    preferred_roles = raw_roles

            preferred_locs: list[str] = []
            raw_loc = profile_row.get("preferred_location")
            if raw_loc:
                preferred_locs = [raw_loc]

            exp_years = 0

            profile = UserProfile(
                full_name=profile_row.get("full_name", ""),
                skills=skills,
                experience_years=exp_years,
                preferred_locations=preferred_locs,
                preferred_roles=preferred_roles,
                summary=profile_row.get("summary", ""),
            )

            profile_dict: dict = {
                "full_name": profile.full_name,
                "skills": skills,
                "summary": profile.summary,
                "preferred_roles": preferred_roles,
                "preferred_locations": preferred_locs,
                "total_years_experience": exp_years,
                "experience_years": exp_years,
            }

            # ── Link unscored jobs to this user ────────────────────
            session.execute(
                text("""
                    INSERT INTO user_jobs (user_id, job_posting_id, status)
                    SELECT :uid, jp.id, 'new'
                    FROM job_postings jp
                    WHERE jp.status = 'new'
                      AND NOT EXISTS (
                        SELECT 1 FROM user_jobs uj
                        WHERE uj.job_posting_id = jp.id AND uj.user_id = :uid
                      )
                    ON CONFLICT (user_id, job_posting_id) DO NOTHING
                """),
                {"uid": user_id},
            )
            session.commit()

            # ── Load unscored jobs (include company for multi-agent) ─
            jobs = session.execute(
                text(
                    "SELECT jp.id, jp.title, c.name as company, jp.location, "
                    "jp.description, jp.source, jp.source_url "
                    "FROM job_postings jp "
                    "LEFT JOIN companies c ON jp.company_id = c.id "
                    "LEFT JOIN match_scores ms ON ms.job_posting_id = jp.id AND ms.user_id = :uid "
                    "WHERE ms.id IS NULL AND jp.status = 'new' "
                    "ORDER BY jp.created_at DESC "
                    "LIMIT 200"
                ),
                {"uid": user_id},
            ).mappings().all()

            # ── Route to the chosen scoring method ─────────────────
            scored = 0

            if scoring_method == "multi_agent":
                scored = _score_multi_agent(
                    session, user_id, profile_dict, jobs,
                )
            else:
                scored = _score_heuristic(
                    session, user_id, profile, jobs,
                )

            session.commit()
        finally:
            session.close()
            engine.dispose()

        logger.info("run_relevance_scoring completed: %d jobs scored", scored)
        return {"scored": scored}

    except Exception as exc:
        logger.exception("run_relevance_scoring failed")
        raise self.retry(exc=exc)


def _score_heuristic(
    session: Session,
    user_id: str,
    profile: UserProfile,
    jobs: list,
) -> int:
    """Score jobs using the existing heuristic keyword-based scorer."""
    from app.agents.job_relevance import score_job

    scored = 0
    for job in jobs:
        job_dict = {
            "title": job.get("title", ""),
            "location": job.get("location", ""),
            "description": job.get("description", ""),
            "company": job.get("company", ""),
            "employment_type": "",
            "source": job.get("source", ""),
            "url": job.get("source_url", ""),
        }
        relevance = score_job(profile, job_dict)

        session.execute(
            text(
                """
                INSERT INTO match_scores
                    (user_id, job_posting_id, overall_score, grade, details)
                VALUES
                    (:uid, :jid, :overall_score, :grade, :details)
                ON CONFLICT (user_id, job_posting_id) DO UPDATE SET
                    overall_score = EXCLUDED.overall_score,
                    grade = EXCLUDED.grade,
                    details = EXCLUDED.details
                """
            ),
            {
                "uid": user_id,
                "jid": str(job["id"]),
                "overall_score": float(relevance.get("total_score", 0)),
                "grade": _grade_from_score(relevance.get("total_score", 0)),
                "details": json.dumps(relevance, ensure_ascii=False),
            },
        )
        scored += 1
    return scored


def _score_multi_agent(
    session: Session,
    user_id: str,
    profile_dict: dict,
    jobs: list,
) -> int:
    """Score jobs using the multi-agent pipeline (vector + web + LLM)."""
    from app.agents.multi_agent_scoring import MultiAgentScorer

    # Build job list in the format MultiAgentScorer expects
    job_list: list[dict] = []
    for job in jobs:
        job_list.append({
            "id": str(job["id"]),
            "title": job.get("title", "") or "",
            "company": job.get("company", "") or "",
            "location": job.get("location", "") or "",
            "description": job.get("description", "") or "",
            "employment_type": "",
            "work_mode": "",
            "source": job.get("source", "") or "",
            "url": job.get("source_url", "") or "",
        })

    scorer = MultiAgentScorer()
    results = scorer.score_all(profile_dict, job_list)

    scored = 0
    for result in results:
        job_id = result.get("id", "")
        if not job_id:
            continue

        total = float(result.get("total_score", 0))
        grade = result.get("grade", "") or _grade_from_score(total)
        details = {k: v for k, v in result.items() if k not in (
            "id", "title", "company", "location", "description",
            "employment_type", "work_mode", "source", "url",
            "vector_score", "skills_ratio", "matched_skills", "missing_skills",
        )}
        details["matched_skills"] = result.get("matched_skills", [])
        details["missing_skills"] = result.get("missing_skills", [])
        details["vector_score"] = result.get("vector_score", 0)

        session.execute(
            text(
                """
                INSERT INTO match_scores
                    (user_id, job_posting_id, overall_score, grade, details)
                VALUES
                    (:uid, :jid, :overall_score, :grade, :details)
                ON CONFLICT (user_id, job_posting_id) DO UPDATE SET
                    overall_score = EXCLUDED.overall_score,
                    grade = EXCLUDED.grade,
                    details = EXCLUDED.details
                """
            ),
            {
                "uid": user_id,
                "jid": job_id,
                "overall_score": total,
                "grade": grade,
                "details": json.dumps(details, ensure_ascii=False),
            },
        )
        scored += 1

    logger.info(
        "Multi-agent scoring: %d results, %d inserted",
        len(results),
        scored,
    )
    return scored


def _grade_from_score(score: float) -> str:
    """Convert numeric score to grade."""
    if score >= 80:
        return "EXCELLENT"
    elif score >= 60:
        return "GOOD"
    elif score >= 40:
        return "FAIR"
    else:
        return "POOR"
