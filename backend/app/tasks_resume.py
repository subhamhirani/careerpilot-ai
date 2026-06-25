"""
CareerPilot AI — Resume Processing Pipeline Task.

Triggered when a user uploads a resume. Creates a ProcessStatus entry
in the database, extracts text, parses structured data via Groq,
and updates progress in real-time.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from celery import current_app as celery_app

logger = logging.getLogger(__name__)


def _get_db():
    """Create a SQLAlchemy session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    return Session(engine), engine


def _update_status(db, process_id: str, **kwargs):
    """Update a ProcessStatus row."""
    from sqlalchemy import text

    sets = ", ".join(f"{k} = :{k}" for k in kwargs)
    kwargs["id"] = process_id
    db.execute(text(f"UPDATE process_statuses SET {sets}, updated_at = NOW() WHERE id = :id"), kwargs)
    db.commit()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    name="app.tasks.process_resume",
    time_limit=300,
    soft_time_limit=240,
)
def process_resume(self, resume_id: str, file_path: str, user_id: str) -> dict:
    """Process an uploaded resume: extract text, parse, create profile.

    Creates ProcessStatus entries in the DB so the frontend can show
    live progress. Steps:
      1. Text extraction (PDF/DOCX)
      2. Resume parsing (Groq LLM)
      3. Skills extraction
      4. Profile creation in DB
    """
    logger.info("process_resume started: resume_id=%s user_id=%s", resume_id, user_id)
    session, engine = _get_db()
    process_id = str(uuid.uuid4())

    try:
        # ── Step 0: Create process status entry ─────────────────
        from sqlalchemy import text

        session.execute(
            text(
                "INSERT INTO process_statuses (id, user_id, task_name, status, progress_pct, current_step, created_at, updated_at) "
                "VALUES (:id, :uid, :name, 'running', 5, 'Starting resume processing...', NOW(), NOW())"
            ),
            {"id": process_id, "uid": user_id, "name": f"Process Resume: {resume_id[:8]}"},
        )
        session.commit()

        # ── Step 1: Extract text ────────────────────────────────
        _update_status(session, process_id, progress_pct=10, current_step="Extracting text from file...")

        from pathlib import Path

        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            from app.agents.resume_analysis import extract_text_from_pdf
            resume_text = extract_text_from_pdf(file_path)
        elif ext in (".docx", ".doc"):
            from app.agents.resume_analysis import extract_text_from_docx
            resume_text = extract_text_from_docx(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                resume_text = f.read()
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        if not resume_text.strip():
            raise ValueError("No text could be extracted from the resume")

        _update_status(session, process_id, progress_pct=30, current_step=f"Extracted {len(resume_text)} characters. Parsing with AI...")

        # ── Step 2: Parse resume with Groq ──────────────────────
        try:
            from app.agents.resume_analysis import ResumeParser

            parser = ResumeParser()
            profile = parser.parse(resume_text)
            logger.info("Resume parsed for: %s", profile.full_name or "<unknown>")
        except Exception as parse_err:
            logger.warning("Groq parsing failed, using fallback: %s", parse_err)
            # Fallback: basic extraction without LLM
            profile = _fallback_parse(resume_text)

        _update_status(session, process_id, progress_pct=60, current_step="Extracting skills and building profile...")

        # ── Step 3: Store resume in DB ──────────────────────────
        from app.models import Resume as ResumeModel, UserProfile as UserProfileModel

        # Check if resume already exists in DB (by file_path)
        existing = session.execute(
            text("SELECT id FROM resumes WHERE file_path = :fp AND user_id = :uid"),
            {"fp": file_path, "uid": user_id},
        ).fetchone()

        if not existing:
            resume_db_id = str(uuid.uuid4())
            session.execute(
                text(
                    "INSERT INTO resumes (id, user_id, filename, file_path, file_type, parsed_text, is_active, created_at, updated_at) "
                    "VALUES (:id, :uid, :title, :fp, :ft, :parsed, true, NOW(), NOW())"
                ),
                {
                    "id": resume_db_id,
                    "uid": user_id,
                    "title": profile.full_name or "Resume",
                    "fp": file_path,
                    "ft": ext.lstrip("."),
                    "parsed": resume_text[:5000],
                },
            )
            session.commit()
        else:
            resume_db_id = str(existing[0])

        _update_status(session, process_id, progress_pct=80, current_step="Creating user profile in database...")

        # ── Step 4: Create/update user profile ──────────────────
        existing_profile = session.execute(
            text("SELECT id FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()

        # Pass dicts directly — psycopg2 auto-converts Python dict → JSONB
        skills_val = profile.skills if isinstance(profile.skills, list) else list(profile.skills)
        exp_val = profile.work_experience if isinstance(profile.work_experience, list) else list(profile.work_experience)
        edu_val = profile.education if isinstance(profile.education, list) else list(profile.education)
        targets_val = profile.target_roles if isinstance(profile.target_roles, list) else list(profile.target_roles)
        locs_val = profile.preferred_locations if isinstance(profile.preferred_locations, list) else list(profile.preferred_locations)

        if not existing_profile:
            session.execute(
                text(
                    "INSERT INTO user_profiles (id, user_id, full_name, phone, summary, created_at, updated_at) "
                    "VALUES (:id, :uid, :name, :phone, :summary, NOW(), NOW())"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "uid": user_id,
                    "name": profile.full_name or "",
                    "phone": profile.phone or "",
                    "summary": profile.summary or "",
                },
            )
        else:
            session.execute(
                text(
                    "UPDATE user_profiles SET full_name = :name, phone = :phone, summary = :summary, "
                    "skills = :skills, experience = :exp, education = :edu, "
                    "total_years_experience = :years, \"current_role\" = :role, target_roles = :targets, "
                    "preferred_location = :locs, updated_at = NOW() WHERE user_id = :uid"
                ),
                {
                    "uid": user_id,
                    "name": profile.full_name or "",
                    "phone": profile.phone or "",
                    "summary": profile.summary or "",
                    "skills": skills_val,
                    "exp": exp_val,
                    "edu": edu_val,
                    "years": profile.total_years_experience,
                    "role": profile.current_role or "",
                    "targets": targets_val,
                    "locs": locs_val,
                },
            )
        session.commit()

        # ── Step 5: Auto-trigger user-specific scrape + scoring ────
        _update_status(session, process_id, progress_pct=90, current_step="Scraping jobs based on your profile...")

        try:
            from app.tasks_scraper import scrape_and_store_jobs, run_relevance_scoring

            # First: trigger a user-specific scrape based on their profile
            scrape_result = scrape_and_store_jobs.delay(user_id=user_id)
            logger.info("Auto-triggered user scrape for user %s: task %s", user_id, scrape_result.id)

            # Then: trigger scoring (will run after scrape completes via auto-trigger in task)
            score_result = run_relevance_scoring.delay(user_id=user_id)
            logger.info("Auto-triggered relevance scoring for user %s: task %s", user_id, score_result.id)
        except Exception as score_err:
            logger.warning("Failed to auto-trigger scrape/score for user %s: %s", user_id, score_err)

        # ── Step 6: Done ────────────────────────────────────────
        _update_status(
            session,
            process_id,
            progress_pct=100,
            status="completed",
            current_step=f"Done! Extracted {len(profile.skills)} skills, {len(profile.work_experience)} experiences.",
        )

        logger.info("process_resume completed: resume_id=%s", resume_id)
        return {
            "status": "completed",
            "resume_id": resume_id,
            "profile_name": profile.full_name,
            "skills_count": len(profile.skills),
            "experience_count": len(profile.work_experience),
        }

    except Exception as exc:
        logger.exception("process_resume failed: resume_id=%s", resume_id)
        try:
            _update_status(
                session,
                process_id,
                status="failed",
                current_step=f"Error: {str(exc)[:200]}",
            )
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        session.close()
        engine.dispose()


def _fallback_parse(resume_text: str) -> object:
    """Basic fallback parser when Groq is unavailable."""
    from app.agents.resume_analysis import UserProfile
    import re

    lines = resume_text.strip().split("\n")
    profile = UserProfile()

    # First non-empty line is often the name
    for line in lines:
        line = line.strip()
        if line and len(line) < 80 and not any(c in line for c in "@:/"):
            profile.full_name = line
            break

    # Extract email
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', resume_text)
    if email_match:
        profile.email = email_match.group()

    # Extract phone
    phone_match = re.search(r'[\+]?[\d\s\-()]{7,15}', resume_text)
    if phone_match:
        profile.phone = phone_match.group().strip()

    # Common tech skills to look for
    tech_skills = [
        "python", "javascript", "typescript", "java", "go", "rust", "c++", "c#",
        "react", "vue", "angular", "next.js", "node.js", "django", "flask", "fastapi",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "git", "ci/cd", "jenkins", "github actions", "gitlab",
        "linux", "nginx", "apache", "caddy",
        "machine learning", "deep learning", "nlp", "computer vision",
        "pandas", "numpy", "pytorch", "tensorflow",
        "rest api", "graphql", "microservices",
        "agile", "scrum", "jira", "confluence",
    ]
    text_lower = resume_text.lower()
    for skill in tech_skills:
        if skill in text_lower:
            profile.skills.append(skill.title())

    # Extract years of experience
    years_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', text_lower)
    if years_match:
        profile.total_years_experience = float(years_match.group(1))

    return profile
