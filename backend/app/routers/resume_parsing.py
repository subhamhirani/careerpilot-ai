"""
CareerPilot AI — Resume Parsing API Router.
Endpoints for parsing uploaded resumes and extracting structured data.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..notification_service import create_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume-parsing", tags=["resume-parsing"])


def _get_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    return Session(engine), engine


def _extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extract text from a PDF or DOCX file."""
    if file_type.upper() == "PDF":
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("PyPDF2 not installed, returning empty text")
            return ""
    elif file_type.upper() == "DOCX":
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx not installed, returning empty text")
            return ""
    return ""


def _parse_resume_with_llm(resume_text: str) -> dict:
    """Use LLM to extract structured data from resume text."""
    try:
        from ..llm_client import query_llm

        prompt = f"""Extract structured data from this resume. Return ONLY valid JSON with these keys:
{{
  "full_name": "string",
  "email": "string",
  "phone": "string",
  "skills": ["skill1", "skill2"],
  "experience": [
    {{"title": "string", "company": "string", "years": number, "description": "string"}}
  ],
  "education": [
    {{"degree": "string", "institution": "string", "year": number}}
  ],
  "certifications": ["cert1", "cert2"],
  "summary": "string",
  "years_of_experience": number
}}

Resume text:
{resume_text[:4000]}

Return ONLY the JSON, no other text."""

        response = query_llm(prompt, max_tokens=2048)
        # Try to parse JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except Exception as e:
        logger.warning("LLM parsing failed: %s", e)

    return {}


class ParseResumeResponse(BaseModel):
    resume_id: str
    status: str
    parsed_data: Optional[dict] = None


@router.post("/parse/{resume_id}")
async def parse_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Parse a resume and extract structured data."""
    session, engine = _get_db()
    try:
        # Get resume from DB
        row = session.execute(
            text("SELECT * FROM resumes WHERE id = :rid AND user_id = :uid"),
            {"rid": resume_id, "uid": user_id},
        ).mappings().fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Resume not found")

        file_path = row.get("file_path", "")
        file_type = row.get("file_type", "PDF")

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Resume file not found on disk")

        # Extract text
        resume_text = _extract_text_from_file(file_path, file_type)

        if not resume_text.strip():
            return {
                "resume_id": resume_id,
                "status": "no_text_extracted",
                "message": "Could not extract text from the resume. The file may be image-based or corrupted.",
                "parsed_data": None,
            }

        # Parse with LLM
        parsed = _parse_resume_with_llm(resume_text)

        # Update resume record with parsed text
        session.execute(
            text("UPDATE resumes SET parsed_text = :pt WHERE id = :rid"),
            {"pt": resume_text[:50000], "rid": resume_id},
        )

        # If we got structured data, update user profile
        if parsed:
            # Check if profile exists
            profile = session.execute(
                text("SELECT id FROM user_profiles WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()

            profile_data = {}
            if parsed.get("full_name"):
                profile_data["full_name"] = parsed["full_name"]
            if parsed.get("skills"):
                profile_data["skills"] = json.dumps(parsed["skills"])
            if parsed.get("experience"):
                profile_data["experience"] = json.dumps(parsed["experience"])
            if parsed.get("education"):
                profile_data["education"] = json.dumps(parsed["education"])
            if parsed.get("certifications"):
                profile_data["certifications"] = json.dumps(parsed["certifications"])
            if parsed.get("summary"):
                profile_data["summary"] = parsed["summary"]

            if profile_data:
                if profile:
                    set_clauses = ", ".join(f"{k} = :{k}" for k in profile_data)
                    profile_data["uid"] = user_id
                    session.execute(
                        text(f"UPDATE user_profiles SET {set_clauses}, updated_at = NOW() WHERE user_id = :uid"),
                        profile_data,
                    )
                else:
                    import uuid as _uuid
                    pid = str(_uuid.uuid4())
                    cols = ["id", "user_id"] + list(profile_data.keys())
                    vals = [pid, user_id] + list(profile_data.values())
                    col_str = ", ".join(cols)
                    val_str = ", ".join(f":{c}" for c in cols)
                    params = dict(zip(cols, vals))
                    session.execute(
                        text(f"INSERT INTO user_profiles ({col_str}) VALUES ({val_str})"),
                        params,
                    )

        session.commit()

        # Create notification
        create_notification(
            user_id=user_id,
            type="resume_parsed",
            title="Resume Parsed",
            message=f"Successfully parsed resume '{row.get('title', 'Resume')}'. "
                    + ("Profile updated with extracted data." if parsed else "No structured data extracted."),
            entity_type="resume",
            entity_id=resume_id,
        )

        return {
            "resume_id": resume_id,
            "status": "parsed" if parsed else "text_extracted",
            "parsed_data": parsed,
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error("Resume parsing failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
    finally:
        session.close()
        engine.dispose()


@router.get("/status/{resume_id}")
async def get_parse_status(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get the parsing status of a resume."""
    session, engine = _get_db()
    try:
        row = session.execute(
            text("SELECT id, title, parsed_text FROM resumes WHERE id = :rid AND user_id = :uid"),
            {"rid": resume_id, "uid": user_id},
        ).mappings().fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Resume not found")

        has_parsed_text = bool(row.get("parsed_text"))

        return {
            "resume_id": resume_id,
            "title": row.get("title", ""),
            "is_parsed": has_parsed_text,
            "parsed_text_preview": (row["parsed_text"][:200] + "...") if has_parsed_text else None,
        }
    finally:
        session.close()
        engine.dispose()
