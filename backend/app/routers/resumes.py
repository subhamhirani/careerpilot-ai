"""
CareerPilot AI — Resume Management API Router.

Endpoints for uploading, listing, and managing resumes.
"""

from __future__ import annotations

import datetime
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..auth import get_current_user_id

router = APIRouter(prefix="/resumes", tags=["resumes"])

UPLOAD_DIR = "/app/storage/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_dsn)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def _to_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid resume id")


def _serialize_resume(row) -> dict:
    file_path = row[2] or ""
    file_type = (row[4] or "").lower()
    content_type = (
        "application/pdf"
        if file_type == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    file_size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
    return {
        "id": str(row[0]),
        "user_id": str(row[1]),
        "file_path": file_path,
        "name": row[3] or "Resume",
        "title": row[3] or "Resume",
        "file_type": (row[4] or "pdf").upper(),
        "content_type": content_type,
        "file_size": file_size,
        "size": file_size,
        "is_active": bool(row[5]),
        "status": "uploaded",
        "skills": [],
        "created_at": row[6].isoformat() if row[6] else None,
        "updated_at": row[7].isoformat() if row[7] else None,
    }


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    name: str = "",
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Upload a new resume (PDF or DOCX) and persist metadata in PostgreSQL."""
    if file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    content = await file.read()
    file_size = len(content)
    resume_id = uuid.uuid4()
    uid = uuid.UUID(user_id)
    ext = "pdf" if file.content_type == "application/pdf" else "docx"
    title = name or (file.filename or "untitled").rsplit(".", 1)[0]
    filepath = os.path.join(UPLOAD_DIR, f"{resume_id}.{ext}")

    with open(filepath, "wb") as f:
        f.write(content)

    existing_count = db.execute(
        text("SELECT COUNT(*) FROM resumes WHERE user_id = :uid"), {"uid": uid}
    ).scalar() or 0
    is_active = existing_count == 0

    db.execute(
        text(
            """
            INSERT INTO resumes (id, user_id, file_path, title, file_type, is_active)
            VALUES (:id, :uid, :file_path, :title, :file_type, :is_active)
            """
        ),
        {
            "id": resume_id,
            "uid": uid,
            "file_path": filepath,
            "title": title,
            "file_type": ext.upper(),
            "is_active": is_active,
        },
    )
    db.commit()

    try:
        from app.tasks_resume import process_resume
        import logging as _logging

        _logging.getLogger(__name__).info(
            "Dispatching process_resume task for resume_id=%s", resume_id
        )
        result = process_resume.delay(
            resume_id=str(resume_id),
            file_path=filepath,
            user_id=user_id,
        )
        _logging.getLogger(__name__).info("process_resume task dispatched: %s", result.id)
    except Exception as task_err:
        import logging

        logging.getLogger(__name__).warning(
            "Failed to dispatch process_resume task: %s", task_err
        )

    return {
        "id": str(resume_id),
        "filename": file.filename,
        "content_type": file.content_type,
        "size": file_size,
        "status": "uploaded",
        "message": "Resume uploaded successfully.",
    }


@router.get("/")
async def list_resumes(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """List all uploaded resumes for the current user."""
    rows = db.execute(
        text(
            """
            SELECT id, user_id, file_path, title, file_type, is_active, created_at, updated_at
            FROM resumes
            WHERE user_id = :uid
            ORDER BY created_at DESC
            """
        ),
        {"uid": uuid.UUID(user_id)},
    ).fetchall()
    resumes = [_serialize_resume(r) for r in rows]
    return {"resumes": resumes, "total": len(resumes)}


@router.get("/{resume_id}")
async def get_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Get a specific resume's details."""
    row = db.execute(
        text(
            """
            SELECT id, user_id, file_path, title, file_type, is_active, created_at, updated_at
            FROM resumes
            WHERE id = :rid AND user_id = :uid
            """
        ),
        {"rid": _to_uuid(resume_id), "uid": uuid.UUID(user_id)},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")
    return _serialize_resume(row)


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Delete a resume."""
    row = db.execute(
        text("SELECT file_path FROM resumes WHERE id = :rid AND user_id = :uid"),
        {"rid": _to_uuid(resume_id), "uid": uuid.UUID(user_id)},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")

    filepath = row[0] or ""
    if filepath and os.path.exists(filepath):
        os.remove(filepath)

    db.execute(
        text("DELETE FROM resumes WHERE id = :rid AND user_id = :uid"),
        {"rid": _to_uuid(resume_id), "uid": uuid.UUID(user_id)},
    )
    db.commit()
    return {"message": "Resume deleted successfully"}


@router.patch("/{resume_id}")
async def update_resume(
    resume_id: str,
    update: dict,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Update resume fields (e.g., set is_active)."""
    rid = _to_uuid(resume_id)
    uid = uuid.UUID(user_id)

    exists = db.execute(
        text("SELECT 1 FROM resumes WHERE id = :rid AND user_id = :uid"),
        {"rid": rid, "uid": uid},
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Resume not found")

    if "is_active" in update:
        is_active = bool(update["is_active"])
        if is_active:
            db.execute(text("UPDATE resumes SET is_active = FALSE WHERE user_id = :uid"), {"uid": uid})
        db.execute(
            text("UPDATE resumes SET is_active = :active, updated_at = NOW() WHERE id = :rid AND user_id = :uid"),
            {"active": is_active, "rid": rid, "uid": uid},
        )

    if "name" in update or "title" in update:
        title = str(update.get("name") or update.get("title"))
        db.execute(
            text("UPDATE resumes SET title = :title, updated_at = NOW() WHERE id = :rid AND user_id = :uid"),
            {"title": title, "rid": rid, "uid": uid},
        )

    db.commit()
    return await get_resume(resume_id, user_id, db)


class TailorResumeRequest(dict):
    """Placeholder for backwards compatibility in OpenAPI-free tests."""
    pass


def _resume_to_json(title: str, parsed_text: str | None) -> dict:
    """Build a minimal resume JSON structure for the tailoring agent."""
    text = parsed_text or ""
    return {
        "full_name": title or "Candidate",
        "summary": text[:1200],
        "experience": [],
        "education": [],
        "skills": [],
        "raw_text": text,
    }


@router.post("/{resume_id}/tailor")
async def tailor_resume_for_job(
    resume_id: str,
    request: dict,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Tailor an uploaded resume to a selected job and persist a resume version."""
    job_id = request.get("job_id") or request.get("job_posting_id")
    if not job_id:
        raise HTTPException(status_code=422, detail="job_id or job_posting_id is required")

    uid = uuid.UUID(user_id)
    rid = _to_uuid(resume_id)
    jid = _to_uuid(job_id)

    resume = db.execute(
        text("""
            SELECT id, title, parsed_text, file_path
            FROM resumes
            WHERE id = :rid AND user_id = :uid
        """),
        {"rid": rid, "uid": uid},
    ).mappings().fetchone()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    job = db.execute(
        text("""
            SELECT jp.id, jp.title, jp.description, jp.location, c.name as company_name
            FROM job_postings jp
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE jp.id = :jid
        """),
        {"jid": jid},
    ).mappings().fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    original_resume = _resume_to_json(resume.get("title") or "Resume", resume.get("parsed_text"))
    job_description = "\n".join([
        f"Title: {job.get('title') or ''}",
        f"Company: {job.get('company_name') or ''}",
        f"Location: {job.get('location') or ''}",
        job.get("description") or "",
    ])

    output_dir = os.getenv("CAREERPILOT_STORAGE", "/app/storage/resume_versions")
    os.makedirs(output_dir, exist_ok=True)

    try:
        from app.agents.resume_tailoring import run_resume_tailoring_task
        result = await run_resume_tailoring_task(
            original_resume=original_resume,
            job_description=job_description,
            original_resume_id=str(rid),
            job_posting_id=str(jid),
            output_dir=output_dir,
        )
        content = __import__("json").dumps(result.get("tailored_json", {}))
        file_path = result.get("pdf_path") or result.get("docx_path")
        change_summary = f"Tailored for {job.get('title') or 'selected job'} at {job.get('company_name') or 'company'}"
    except Exception as exc:
        # Keep the workflow usable when the LLM provider/API key is unavailable.
        content = __import__("json").dumps(original_resume)
        file_path = resume.get("file_path")
        change_summary = f"Fallback tailoring copy for job {jid}: {exc}"

    latest_version = db.execute(
        text("SELECT COALESCE(MAX(version_number), 0) FROM resume_versions WHERE resume_id = :rid"),
        {"rid": rid},
    ).scalar() or 0
    version_id = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO resume_versions
                (id, resume_id, version_number, content, file_path, change_summary)
            VALUES
                (:id, :rid, :version_number, :content, :file_path, :change_summary)
        """),
        {
            "id": version_id,
            "rid": rid,
            "version_number": int(latest_version) + 1,
            "content": content,
            "file_path": file_path,
            "change_summary": change_summary,
        },
    )
    db.commit()

    return {
        "id": str(version_id),
        "resume_id": str(rid),
        "job_posting_id": str(jid),
        "version_number": int(latest_version) + 1,
        "file_path": file_path,
        "change_summary": change_summary,
        "content": content,
    }


@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Download a resume file."""
    resume = await get_resume(resume_id, user_id, db)
    filepath = resume.get("file_path", "")
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        filepath,
        media_type=resume.get("content_type", "application/octet-stream"),
        filename=f"{resume['name']}.{resume['file_type'].lower()}",
    )
