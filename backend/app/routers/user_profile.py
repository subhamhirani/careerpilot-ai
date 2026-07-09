"""
CareerPilot AI — User Profile API Router.
Endpoints for viewing and editing the user profile.
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
from sqlalchemy.orm import Session

from ..auth import get_current_user_id


def _to_uuid(value) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/user-profile", tags=["user-profile"])


def _get_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    return Session(engine), engine


# Columns that actually exist in the user_profiles table:
# id, user_id, raw_json, embedding, parsed_at, full_name, phone, summary,
# skills, experience, education, total_years_experience, current_role,
# target_roles, preferred_location, created_at, updated_at

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[list] = None
    experience: Optional[list] = None
    education: Optional[list] = None
    preferred_location: Optional[str] = None
    preferred_roles: Optional[list] = None
    current_role: Optional[str] = None
    total_years_experience: Optional[float] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    certifications: Optional[list] = None


class UpdateLocationRequest(BaseModel):
    preferred_location: str


@router.get("/")
async def get_profile(user_id: str = Depends(get_current_user_id)):
    """Get the current user's profile."""
    session, engine = _get_db()
    try:
        uid = _to_uuid(user_id)
        row = session.execute(
            text("SELECT * FROM user_profiles WHERE user_id = :uid"),
            {"uid": uid},
        ).mappings().fetchone()

        if not row:
            return {
                "id": None,
                "user_id": user_id,
                "full_name": "",
                "phone": "",
                "headline": "",
                "summary": "",
                "skills": [],
                "experience": [],
                "education": [],
                "preferred_roles": [],
                "preferred_location": "",
                "current_role": "",
                "total_years_experience": 0,
                "linkedin_url": "",
                "github_url": "",
                "portfolio_url": "",
                "certifications": [],
            }

        def _parse_json(val):
            if val is None:
                return []
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    return val
            return val

        headline_val = row.get("headline", "") or row.get("current_role", "") or ""
        return {
            "id": str(row["id"]) if row.get("id") else None,
            "user_id": user_id,
            "full_name": row.get("full_name", "") or "",
            "phone": row.get("phone", "") or "",
            "headline": headline_val,
            "summary": row.get("summary", "") or "",
            "skills": _parse_json(row.get("skills")),
            "experience": _parse_json(row.get("experience")),
            "education": _parse_json(row.get("education")),
            "preferred_roles": _parse_json(row.get("preferred_roles")),
            "preferred_location": row.get("preferred_location", "") or "",
            "current_role": row.get("current_role", "") or "",
            "total_years_experience": row.get("total_years_experience", 0) or 0,
            "linkedin_url": row.get("linkedin_url", "") or "",
            "github_url": row.get("github_url", "") or "",
            "portfolio_url": row.get("portfolio_url", "") or "",
            "certifications": _parse_json(row.get("certifications")),
        }
    finally:
        session.close()
        engine.dispose()


@router.put("/")
async def update_profile(
    update: UpdateProfileRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update the current user's profile. Creates if not exists."""
    session, engine = _get_db()
    try:
        uid = _to_uuid(user_id)
        existing = session.execute(
            text("SELECT id FROM user_profiles WHERE user_id = :uid"),
            {"uid": uid},
        ).fetchone()

        data = update.model_dump(exclude_none=True)

        if existing:
            # Build dynamic UPDATE — only use columns that exist in DB
            set_clauses = []
            params: dict[str, Any] = {"uid": uid}
            for key, value in data.items():
                if key in ("skills", "experience", "education", "preferred_roles", "certifications"):
                    value = json.dumps(value)
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

            set_clauses.append("updated_at = NOW()")
            query = f"UPDATE user_profiles SET {', '.join(set_clauses)} WHERE user_id = :uid"
            session.execute(text(query), params)
        else:
            new_id = str(uuid.uuid4())
            cols = ["id", "user_id"]
            params = {"id": new_id, "user_id": uid}
            for key, value in data.items():
                if key in ("skills", "experience", "education", "preferred_roles", "certifications"):
                    value = json.dumps(value)
                cols.append(key)
                params[key] = value

            col_str = ", ".join(cols)
            val_str = ", ".join(f":{c}" for c in cols)
            session.execute(
                text(f"INSERT INTO user_profiles ({col_str}) VALUES ({val_str})"),
                params,
            )

        session.commit()

        # Return updated profile directly (avoid redirect from get_profile)
        row = session.execute(
            text("SELECT * FROM user_profiles WHERE user_id = :uid"),
            {"uid": uid},
        ).mappings().fetchone()

        def _parse_json(val):
            if val is None:
                return []
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    return val
            return val

        headline_val = (row.get("headline", "") or row.get("current_role", "") or "") if row else ""
        return {
            "id": str(row["id"]) if row and row.get("id") else None,
            "user_id": user_id,
            "full_name": (row.get("full_name", "") or "") if row else "",
            "phone": (row.get("phone", "") or "") if row else "",
            "headline": headline_val,
            "summary": (row.get("summary", "") or "") if row else "",
            "skills": _parse_json(row.get("skills")) if row else [],
            "experience": _parse_json(row.get("experience")) if row else [],
            "education": _parse_json(row.get("education")) if row else [],
            "preferred_roles": _parse_json(row.get("preferred_roles")) if row else [],
            "preferred_location": (row.get("preferred_location", "") or "") if row else "",
            "current_role": (row.get("current_role", "") or "") if row else "",
            "total_years_experience": (row.get("total_years_experience", 0) or 0) if row else 0,
            "linkedin_url": (row.get("linkedin_url", "") or "") if row else "",
            "github_url": (row.get("github_url", "") or "") if row else "",
            "portfolio_url": (row.get("portfolio_url", "") or "") if row else "",
            "certifications": _parse_json(row.get("certifications")) if row else [],
        }
    except Exception as e:
        session.rollback()
        logger.error("Failed to update profile: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update profile")
    finally:
        session.close()
        engine.dispose()


# ── Location-specific endpoints ───────────────────────────────────────────

@router.get("/location")
async def get_location(user_id: str = Depends(get_current_user_id)):
    """Return the user's current preferred location."""
    session, engine = _get_db()
    try:
        uid = _to_uuid(user_id)
        row = session.execute(
            text("SELECT preferred_location FROM user_profiles WHERE user_id = :uid"),
            {"uid": uid},
        ).mappings().fetchone()
        return {"preferred_location": row.get("preferred_location", "") or ""} if row else {"preferred_location": ""}
    finally:
        session.close()
        engine.dispose()


@router.put("/location")
async def update_location(
    update: UpdateLocationRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update the user's preferred location without touching other profile fields."""
    session, engine = _get_db()
    try:
        uid = _to_uuid(user_id)
        existing = session.execute(
            text("SELECT id FROM user_profiles WHERE user_id = :uid"),
            {"uid": uid},
        ).fetchone()

        if existing:
            session.execute(
                text("UPDATE user_profiles SET preferred_location = :loc, updated_at = NOW() WHERE user_id = :uid"),
                {"loc": update.preferred_location, "uid": uid},
            )
        else:
            new_id = str(uuid.uuid4())
            session.execute(
                text(
                    "INSERT INTO user_profiles (id, user_id, preferred_location, created_at, updated_at) "
                    "VALUES (:id, :uid, :loc, NOW(), NOW())"
                ),
                {"id": new_id, "uid": uid, "loc": update.preferred_location},
            )
        session.commit()
        return {"preferred_location": update.preferred_location}
    except Exception as e:
        session.rollback()
        logger.error("Failed to update location: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update location")
    finally:
        session.close()
        engine.dispose()
