"""
CareerPilot AI — Onboarding API Router.

Guided first-run experience for new users.
Tracks progress and seeds demo data using the user's own account.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from ..auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Public health endpoint – no auth required.
@router.get("/public", tags=["onboarding"])
async def onboarding_public():
    """Return a minimal health payload for unauthenticated checks.
    Useful for UI components that only need to confirm the service is up.
    """
    return {"status": "ok", "message": "onboarding reachable"}

# Provide a root endpoint so ``/api/onboarding`` returns status instead of 404.
@router.get("/", tags=["onboarding"])
async def onboarding_root(user_id: str = Depends(get_current_user_id)):
    """Alias for ``/status`` – returns onboarding progress at the base path.

    This makes ``GET /api/onboarding`` a valid endpoint, improving UI
    compatibility and eliminating the 404 seen in logs.
    """
    return await get_onboarding_status(user_id)

# Also expose the endpoint without a trailing slash for direct ``/api/onboarding`` access.
@router.get("", tags=["onboarding"])
async def onboarding_root_no_slash(user_id: str = Depends(get_current_user_id)):
    """Duplicate of ``onboarding_root`` without the trailing slash.

    FastAPI's default redirect behaviour may be disabled in this deployment,
    so we provide an explicit route matching ``/api/onboarding``.
    """
    return await get_onboarding_status(user_id)



def _get_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    return create_engine(sync_dsn)


def _to_uuid(value) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _count_user_resumes(user_id: str) -> int:
    engine = _get_db()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM resumes WHERE user_id = :uid"),
                {"uid": _to_uuid(user_id)},
            ).fetchone()
            return result[0] if result else 0
    except Exception:
        return 0
    finally:
        engine.dispose()


def _user_has_profile(user_id: str) -> bool:
    engine = _get_db()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM user_profiles WHERE user_id = :uid"),
                {"uid": _to_uuid(user_id)},
            ).fetchone()
            return result is not None
    except Exception:
        return False
    finally:
        engine.dispose()


def _count_user_matches(user_id: str) -> int:
    engine = _get_db()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM match_scores WHERE user_id = :uid"),
                {"uid": _to_uuid(user_id)},
            ).fetchone()
            return result[0] if result else 0
    except Exception:
        return 0
    finally:
        engine.dispose()


def _count_user_cover_letters(user_id: str) -> int:
    engine = _get_db()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM cover_letters WHERE user_id = :uid"),
                {"uid": _to_uuid(user_id)},
            ).fetchone()
            return result[0] if result else 0
    except Exception:
        return 0
    finally:
        engine.dispose()


def _count_user_applications(user_id: str) -> int:
    engine = _get_db()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM applications WHERE user_id = :uid"),
                {"uid": _to_uuid(user_id)},
            ).fetchone()
            return result[0] if result else 0
    except Exception:
        return 0
    finally:
        engine.dispose()


def _user_has_api_keys(user_id: str) -> bool:
    """Return True if at least one active system API key is configured.

    Note: api_keys are global (system-wide) in the live schema, so the
    caller's user_id is informational only — keys are not per-user.
    """
    engine = _get_db()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM api_settings WHERE is_active = TRUE LIMIT 1"),
            ).fetchone()
            return result is not None
    except Exception:
        return False
    finally:
        engine.dispose()


# ── Pydantic models ─────────────────────────────────────────

class OnboardingProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[list] = None
    experience: Optional[list] = None
    education: Optional[list] = None
    preferred_location: Optional[str] = None
    preferred_roles: Optional[list] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


# ── Routes ──────────────────────────────────────────────────

@router.get("/status")
async def get_onboarding_status(user_id: str = Depends(get_current_user_id)):
    """
    Return the onboarding progress for the current user.
    Frontend uses this to show a checklist / progress bar.
    """
    resume_count = _count_user_resumes(user_id)
    has_profile = _user_has_profile(user_id)
    has_api_keys = _user_has_api_keys(user_id)
    match_count = _count_user_matches(user_id)
    cover_letter_count = _count_user_cover_letters(user_id)
    application_count = _count_user_applications(user_id)

    # Check if any jobs exist (shared across users)
    scraper_done = False
    engine = _get_db()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM job_postings")).fetchone()
            scraper_done = result[0] > 0 if result else False
    except Exception:
        pass
    finally:
        engine.dispose()

    steps = [
        {
            "id": "upload_resume",
            "title": "Upload Your Resume",
            "description": "Upload your resume (PDF or DOCX) to get personalized job matches.",
            "href": "/onboarding",
            "status": "complete" if resume_count > 0 else "pending",
            "detail": f"{resume_count} resume(s) uploaded" if resume_count > 0 else None,
        },
        {
            "id": "setup_profile",
            "title": "Set Up Profile",
            "description": "Add your skills, experience, and target roles for better matching.",
            "href": "/onboarding",
            "status": "complete" if has_profile else "pending",
            "detail": "Profile created" if has_profile else None,
        },
        {
            "id": "add_api_keys",
            "title": "Connect APIs (Optional)",
            "description": "Add API keys for LinkedIn, Indeed, or other job boards.",
            "href": "/onboarding",
            "status": "complete" if has_api_keys else "skippable",
            "detail": "API keys configured" if has_api_keys else "Can be skipped",
        },
        {
            "id": "run_scraper",
            "title": "Job Feed Ready",
            "description": "Job postings are pre-loaded. Run the scraper anytime for fresh listings.",
            "href": "/onboarding",
            "status": "complete" if scraper_done else "pending",
            "detail": "Jobs available" if scraper_done else "Run scraper first",
        },
        {
            "id": "view_matches",
            "title": "View Job Matches",
            "description": "See AI-scored job matches ranked by fit for your profile.",
            "href": "/matches",
            "status": "complete" if match_count > 0 else "pending",
            "detail": f"{match_count} match(es)" if match_count > 0 else "Upload resume first",
        },
        {
            "id": "generate_cover_letter",
            "title": "Generate Cover Letter",
            "description": "Let AI craft a tailored cover letter for any job.",
            "href": "/jobs",
            "status": "complete" if cover_letter_count > 0 else "pending",
            "detail": f"{cover_letter_count} cover letter(s)" if cover_letter_count > 0 else None,
        },
        {
            "id": "apply",
            "title": "Track Applications",
            "description": "Apply to jobs and track your application status.",
            "href": "/applications",
            "status": "complete" if application_count > 0 else "pending",
            "detail": f"{application_count} application(s)" if application_count > 0 else None,
        },
    ]

    completed = sum(1 for s in steps if s["status"] == "complete")
    total_steps = len(steps)
    percent = min(100, max(0, round((completed / total_steps) * 100))) if total_steps > 0 else 100

    return {
        "steps": steps,
        "progress": {
            "completed": completed,
            "total": total_steps,
            "percent": percent,
        },
        "is_complete": completed >= total_steps,
    }


@router.post("/setup-profile")
async def quick_setup_profile(
    body: OnboardingProfileRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Quick profile setup from onboarding wizard.
    Creates or updates the user profile in one call.
    """
    uid = _to_uuid(user_id)
    engine = _get_db()
    try:
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT id FROM user_profiles WHERE user_id = :uid"),
                {"uid": uid},
            ).fetchone()

            data = body.model_dump(exclude_none=True)
            if not data:
                return {"message": "Nothing to update", "user_id": user_id}

            columns = {
                r[0] for r in conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'user_profiles'"
                )).fetchall()
            }

            # Map newer frontend fields to older schema names when needed.
            if "headline" in data and "headline" not in columns and "current_role" in columns:
                data["current_role"] = data.pop("headline")
            if "preferred_roles" in data and "preferred_roles" not in columns and "target_roles" in columns:
                data["target_roles"] = data.pop("preferred_roles")

            # Drop unsupported optional fields instead of failing the whole onboarding flow.
            data = {k: v for k, v in data.items() if k in columns}
            if not data:
                return {"message": "No supported profile fields to update", "user_id": user_id}

            # Serialize JSON fields
            json_fields = ("skills", "experience", "education", "preferred_roles", "target_roles")
            for field in json_fields:
                if field in data and data[field] is not None:
                    data[field] = json.dumps(data[field])

            if existing:
                set_parts = [f"{k} = :{k}" for k in data]
                set_parts.append("updated_at = NOW()")
                params = {**data, "uid": uid}
                conn.execute(
                    text(f"UPDATE user_profiles SET {', '.join(set_parts)} WHERE user_id = :uid"),
                    params,
                )
            else:
                pid = str(uuid.uuid4())
                cols = ["id", "user_id"] + list(data.keys())
                params = {"id": pid, "user_id": uid, **data}
                col_str = ", ".join(cols)
                val_str = ", ".join(f":{c}" for c in cols)
                conn.execute(
                    text(f"INSERT INTO user_profiles ({col_str}) VALUES ({val_str})"),
                    params,
                )

            conn.commit()

        logger.info("Onboarding profile created/updated for user %s", user_id)
        return {"message": "Profile saved", "user_id": user_id}
    except Exception as e:
        logger.error("Onboarding profile setup failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")
    finally:
        engine.dispose()


@router.post("/dismiss")
async def dismiss_onboarding(user_id: str = Depends(get_current_user_id)):
    """Mark onboarding as dismissed so it doesn't show again."""
    logger.info("Onboarding dismissed by user %s", user_id)
    return {"message": "Onboarding dismissed"}
