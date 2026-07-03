"""
CareerPilot AI — Cover Letter API Router.
Endpoints for generating, listing, and managing cover letters.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..agents.cover_letter_generator import generate_cover_letter, generate_cover_letter_short
from ..auth import get_current_user_id
from ..notification_service import create_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


def _get_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    return Session(engine), engine


class GenerateRequest(BaseModel):
    job_id: Optional[str] = None
    job_posting_id: Optional[str] = None
    tone: str = "professional"  # professional, casual, enthusiastic
    short: bool = False

    def resolved_job_id(self) -> str:
        job_id = self.job_id or self.job_posting_id
        if not job_id:
            raise ValueError("job_id or job_posting_id is required")
        return job_id


def _to_uuid(value: str) -> uuid.UUID:
    """Convert string to UUID, handling both dashed and non-dashed formats."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


@router.post("/generate")
async def generate(
    request: GenerateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a cover letter for a specific job."""
    session, engine = _get_db()
    try:
        uid = _to_uuid(user_id)
        try:
            jid = _to_uuid(request.resolved_job_id())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        # Load job with company name
        job = session.execute(
            text(
                "SELECT jp.*, c.name as company_name "
                "FROM job_postings jp "
                "LEFT JOIN companies c ON jp.company_id = c.id "
                "WHERE jp.id = :jid"
            ),
            {"jid": jid},
        ).mappings().fetchone()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Load user profile
        profile_row = session.execute(
            text(
                "SELECT full_name, skills, experience, summary, "
                "preferred_location, preferred_roles "
                "FROM user_profiles WHERE user_id = :uid"
            ),
            {"uid": uid},
        ).mappings().fetchone()

        if not profile_row:
            raise HTTPException(status_code=404, detail="User profile not found. Please set up your profile first.")

        # Build profile dict
        skills = []
        if profile_row.get("skills"):
            s = profile_row["skills"]
            if isinstance(s, str):
                s = json.loads(s)
            if isinstance(s, list):
                skills = s
            elif isinstance(s, dict):
                for v in s.values():
                    if isinstance(v, list):
                        skills.extend(v)

        preferred_roles = []
        if profile_row.get("preferred_roles"):
            r = profile_row["preferred_roles"]
            if isinstance(r, str):
                r = json.loads(r)
            if isinstance(r, list):
                preferred_roles = r

        exp_years = 0.0
        if profile_row.get("experience"):
            e = profile_row["experience"]
            if isinstance(e, str):
                e = json.loads(e)
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
            "preferred_roles": preferred_roles,
            "preferred_locations": [profile_row["preferred_location"]] if profile_row.get("preferred_location") else [],
        }

        job_dict = {
            "title": job.get("title", ""),
            "company": job.get("company_name") or "",
            "location": job.get("location", ""),
            "description": job.get("description", "") or "",
            "skills": [],
            "experience_required": job.get("experience_required", "") or "",
            "employment_type": job.get("employment_type", "") or "",
        }

        if request.short:
            letter = generate_cover_letter_short(profile, job_dict)
        else:
            letter = generate_cover_letter(profile, job_dict)

        # Store in DB, supporting both current and legacy cover_letters schemas.
        cl_id = str(uuid.uuid4())
        word_count = len(letter.split())
        try:
            columns = {
                r[0] for r in session.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'cover_letters'"
                )).fetchall()
            }
            insert_cols = ["id", "user_id", "job_posting_id", "content", "tone"]
            params = {
                "id": cl_id,
                "uid": uid,
                "jid": jid,
                "content": letter,
                "tone": request.tone,
                "title": f"Cover Letter - {job_dict['title']}",
                "word_count": word_count,
            }
            if "title" in columns:
                insert_cols.append("title")
            if "word_count" in columns:
                insert_cols.append("word_count")
            col_sql = ", ".join(insert_cols)
            value_map = {
                "id": ":id",
                "user_id": ":uid",
                "job_posting_id": ":jid",
                "content": ":content",
                "tone": ":tone",
                "title": ":title",
                "word_count": ":word_count",
            }
            val_sql = ", ".join(value_map[c] for c in insert_cols)
            session.execute(text(f"INSERT INTO cover_letters ({col_sql}) VALUES ({val_sql})"), params)
            session.commit()
        except Exception as db_err:
            session.rollback()
            logger.warning("Failed to store cover letter: %s", db_err)
            cl_id = None

        # Create notification
        create_notification(
            user_id=user_id,
            type="cover_letter_generated",
            title="Cover Letter Generated",
            message=f"Generated cover letter for {job_dict['title']} at {job_dict['company']}",
            entity_type="cover_letter",
            entity_id=cl_id or "",
        )

        return {
            "cover_letter": letter,
            "content": letter,
            "title": f"Cover Letter - {job_dict['title']}",
            "word_count": word_count,
            "job_title": job_dict["title"],
            "company": job_dict["company"],
            "tone": request.tone,
            "id": cl_id,
        }
    finally:
        session.close()
        engine.dispose()


@router.get("/")
async def list_cover_letters(
    job_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
):
    """List cover letters for the current user."""
    session, engine = _get_db()
    try:
        uid = _to_uuid(user_id)
        query = "SELECT * FROM cover_letters WHERE user_id = :uid"
        params: dict = {"uid": uid}

        if job_id:
            query += " AND job_posting_id = :jid"
            params["jid"] = _to_uuid(job_id)

        order_col = "created_at"
        columns = {r[0] for r in session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'cover_letters'")).fetchall()}
        if "created_at" not in columns and "generated_at" in columns:
            order_col = "generated_at"
        query += f" ORDER BY {order_col} DESC LIMIT :limit"
        params["limit"] = limit

        rows = session.execute(text(query), params).mappings().all()

        results = []
        for row in rows:
            results.append({
                "id": str(row["id"]),
                "job_posting_id": str(row["job_posting_id"]) if row.get("job_posting_id") else None,
                "content": row.get("content", ""),
                "tone": row.get("tone", "formal"),
                "title": row.get("title") or "Cover Letter",
                "word_count": row.get("word_count") or len((row.get("content") or "").split()),
                "created_at": (row.get("created_at") or row.get("generated_at")).isoformat() if (row.get("created_at") or row.get("generated_at")) else None,
            })

        return {"cover_letters": results, "total": len(results)}
    finally:
        session.close()
        engine.dispose()


@router.get("/{cover_letter_id}")
async def get_cover_letter(
    cover_letter_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific cover letter."""
    session, engine = _get_db()
    try:
        row = session.execute(
            text("SELECT * FROM cover_letters WHERE id = :cid AND user_id = :uid"),
            {"cid": _to_uuid(cover_letter_id), "uid": _to_uuid(user_id)},
        ).mappings().fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Cover letter not found")

        return {
            "id": str(row["id"]),
            "job_posting_id": str(row["job_posting_id"]) if row.get("job_posting_id") else None,
            "content": row.get("content", ""),
            "tone": row.get("tone", "formal"),
            "title": row.get("title") or "Cover Letter",
            "word_count": row.get("word_count") or len((row.get("content") or "").split()),
            "created_at": (row.get("created_at") or row.get("generated_at")).isoformat() if (row.get("created_at") or row.get("generated_at")) else None,
        }
    finally:
        session.close()
        engine.dispose()


@router.delete("/{cover_letter_id}")
async def delete_cover_letter(
    cover_letter_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a cover letter."""
    session, engine = _get_db()
    try:
        result = session.execute(
            text("DELETE FROM cover_letters WHERE id = :cid AND user_id = :uid"),
            {"cid": _to_uuid(cover_letter_id), "uid": _to_uuid(user_id)},
        )
        session.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Cover letter not found")

        return {"message": "Cover letter deleted"}
    finally:
        session.close()
        engine.dispose()
