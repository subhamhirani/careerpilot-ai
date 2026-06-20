"""
CareerPilot AI — Resume Management API Router.

Endpoints for uploading, listing, and managing resumes.
"""

from __future__ import annotations
import os
import uuid
import shutil
import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..auth import get_current_user_id
from ..state import get_resumes, add_resume, remove_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])

# In-memory resume store (per container lifetime)
UPLOAD_DIR = "/app/storage/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    name: str = "",
    user_id: str = Depends(get_current_user_id),
):
    """Upload a new resume (PDF or DOCX)."""
    if file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    # Read file content
    content = await file.read()
    file_size = len(content)
    resume_id = str(uuid.uuid4())
    ext = "pdf" if file.content_type == "application/pdf" else "docx"
    stored_filename = f"{resume_id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, stored_filename)

    # Save to disk
    with open(filepath, "wb") as f:
        f.write(content)

    # Determine if this should be the active resume (first for the user)
    user_resumes = [r for r in get_resumes() if r["user_id"] == user_id]
    is_active = len(user_resumes) == 0

    resume_record = {
        "id": resume_id,
        "user_id": user_id,
        "name": name or (file.filename or "untitled").rsplit(".", 1)[0],
        "file_type": ext.upper(),
        "file_size": file_size,
        "file_path": filepath,
        "content_type": file.content_type,
        "is_active": is_active,
        "skills": [],
        "status": "uploaded",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }
    add_resume(resume_record)

    # Trigger async resume processing pipeline
    try:
        from app.tasks_resume import process_resume
        import logging as _logging
        _logging.getLogger(__name__).info("Dispatching process_resume task for resume_id=%s", resume_id)
        result = process_resume.delay(
            resume_id=resume_id,
            file_path=filepath,
            user_id=user_id,
        )
        _logging.getLogger(__name__).info("process_resume task dispatched: %s", result.id)
    except Exception as task_err:
        # Don't fail the upload if task dispatch fails
        import logging
        logging.getLogger(__name__).warning(
            "Failed to dispatch process_resume task: %s", task_err
        )

    return {
        "id": resume_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size": file_size,
        "status": "uploaded",
        "message": "Resume uploaded successfully.",
    }


@router.get("/")
async def list_resumes(user_id: str = Depends(get_current_user_id)):
    """List all uploaded resumes for the current user."""
    all_resumes = get_resumes()
    user_resumes = [r for r in all_resumes if r["user_id"] == user_id]
    # Return newest first
    user_resumes.sort(key=lambda r: r["created_at"], reverse=True)
    return {"resumes": user_resumes, "total": len(user_resumes)}


@router.get("/{resume_id}")
async def get_resume(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Get a specific resume's details."""
    for r in get_resumes():
        if r["id"] == resume_id and r["user_id"] == user_id:
            return r
    raise HTTPException(status_code=404, detail="Resume not found")


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete a resume."""
    resumes_list = get_resumes()
    for i, r in enumerate(resumes_list):
        if r["id"] == resume_id and r["user_id"] == user_id:
            filepath = r.get("file_path", "")
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            resumes_list.pop(i)
            return {"message": "Resume deleted successfully"}
    raise HTTPException(status_code=404, detail="Resume not found")


@router.patch("/{resume_id}")
async def update_resume(
    resume_id: str,
    update: dict,
    user_id: str = Depends(get_current_user_id),
):
    """Update resume fields (e.g., set is_active)."""
    resumes_list = get_resumes()
    for r in resumes_list:
        if r["id"] == resume_id and r["user_id"] == user_id:
            if "is_active" in update:
                r["is_active"] = bool(update["is_active"])
                if r["is_active"]:
                    # Deactivate all other resumes for this user
                    for other in resumes_list:
                        if other["user_id"] == user_id and other["id"] != resume_id:
                            other["is_active"] = False
            if "name" in update:
                r["name"] = str(update["name"])
            r["updated_at"] = datetime.datetime.utcnow().isoformat()
            return r
    raise HTTPException(status_code=404, detail="Resume not found")


@router.get("/{resume_id}/download")
async def download_resume(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Download a resume file."""
    for r in get_resumes():
        if r["id"] == resume_id and r["user_id"] == user_id:
            filepath = r.get("file_path", "")
            if not filepath or not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail="File not found")
            from fastapi.responses import FileResponse
            return FileResponse(
                filepath,
                media_type=r.get("content_type", "application/octet-stream"),
                filename=f"{r['name']}.{r['file_type'].lower()}",
            )
    raise HTTPException(status_code=404, detail="Resume not found")
