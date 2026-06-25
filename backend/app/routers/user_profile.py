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
    summary: Optional[str] = None
    skills: Optional[list] = None
    experience: Optional[list] = None
    education: Optional[list] = None
    preferred_location: Optional[str] = None
    target_roles: Optional[list] = None
    current_role: Optional[str] = None
    total_years_experience: Optional[float] = None


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
                "summary": "",
                "skills": [],
                "experience": [],
                "education": [],
                "target_roles": [],
                "preferred_location": "",
                "current_role": "",
                "total_years_experience": 0,
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

        return {
            "id": str(row["id"]) if row.get("id") else None,
            "user_id": user_id,
            "full_name": row.get("full_name", "") or "",
            "phone": row.get("phone", "") or "",
            "summary": row.get("summary", "") or "",
            "skills": _parse_json(row.get("skills")),
            "experience": _parse_json(row.get("experience")),
            "education": _parse_json(row.get("education")),
            "target_roles": _parse_json(row.get("target_roles")),
            "preferred_location": row.get("preferred_location", "") or "",
            "current_role": row.get("current_role", "") or "",
            "total_years_experience": row.get("total_years_experience", 0) or 0,
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
                if key in ("skills", "experience", "education", "target_roles"):
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
                if key in ("skills", "experience", "education", "target_roles"):
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

        return {
            "id": str(row["id"]) if row and row.get("id") else None,
            "user_id": user_id,
            "full_name": (row.get("full_name", "") or "") if row else "",
            "phone": (row.get("phone", "") or "") if row else "",
            "summary": (row.get("summary", "") or "") if row else "",
            "skills": _parse_json(row.get("skills")) if row else [],
            "experience": _parse_json(row.get("experience")) if row else [],
            "education": _parse_json(row.get("education")) if row else [],
            "target_roles": _parse_json(row.get("target_roles")) if row else [],
            "preferred_location": (row.get("preferred_location", "") or "") if row else "",
            "current_role": (row.get("current_role", "") or "") if row else "",
            "total_years_experience": (row.get("total_years_experience", 0) or 0) if row else 0,
        }
    except Exception as e:
        session.rollback()
        logger.error("Failed to update profile: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update profile")
    finally:
        session.close()
        engine.dispose()
