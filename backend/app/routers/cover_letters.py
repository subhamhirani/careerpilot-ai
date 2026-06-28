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
from pydantic import BaseModel
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
    job_id: str
    tone: str = "professional"  # professional, casual, enthusiastic
    short: bool = False


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
        jid = _to_uuid(request.job_id)

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

        # Store in DB — columns: id, job_posting_id, user_id, content, tone, generated_at
        cl_id = str(uuid.uuid4())
        try:
            session.execute(
                text(
                    """
                    INSERT INTO cover_letters
                        (id, user_id, job_posting_id, content, tone)
                    VALUES
                        (:id, :uid, :jid, :content, :tone)
                    """
                ),
                {
                    "id": cl_id,
                    "uid": uid,
                    "jid": jid,
                    "content": letter,
                    "tone": request.tone,
                },
            )
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
            "word_count": len(letter.split()),
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

        query += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit

        rows = session.execute(text(query), params).mappings().all()

        results = []
        for row in rows:
            results.append({
                "id": str(row["id"]),
                "job_posting_id": str(row["job_posting_id"]) if row.get("job_posting_id") else None,
                "content": row.get("content", ""),
                "tone": row.get("tone", "formal"),
                "generated_at": row["created_at"].isoformat() if row.get("created_at") else None,
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
            "generated_at": row["created_at"].isoformat() if row.get("created_at") else None,
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
