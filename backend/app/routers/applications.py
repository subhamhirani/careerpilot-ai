"""
CareerPilot AI — Applications API Router.

Endpoints for tracking submitted applications and their status.
"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..auth import get_current_user_id

router = APIRouter(prefix="/applications", tags=["applications"])


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


def _to_uuid(value) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


@router.get("/")
async def list_applications(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """List all submitted applications with status tracking."""
    uid = _to_uuid(user_id)
    conditions = ["a.user_id = :uid"]
    params = {"uid": uid, "limit": limit, "offset": offset}

    if status:
        conditions.append("a.status = :status")
        params["status"] = status

    where = " AND ".join(conditions)

    count_sql = f"SELECT COUNT(*) FROM applications a WHERE {where}"
    total = db.execute(text(count_sql), params).scalar() or 0

    rows = db.execute(
        text(f"""
            SELECT a.id, a.job_posting_id, a.status, a.method,
                   a.applied_at,
                   jp.title, jp.location, c.name as company_name,
                   ms.score as match_score, jp.source
            FROM applications a
            JOIN job_postings jp ON a.job_posting_id = jp.id
            LEFT JOIN companies c ON jp.company_id = c.id
            LEFT JOIN match_scores ms ON ms.job_posting_id = a.job_posting_id AND ms.user_id = a.user_id
            WHERE {where}
            ORDER BY a.applied_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).fetchall()

    applications = []
    for row in rows:
        applications.append({
            "id": str(row[0]),
            "job_posting_id": str(row[1]),
            "status": row[2],
            "method": row[3],
            "submitted_at": row[4].isoformat() if row[4] else None,
            "match_score": row[8] if row[8] is not None else None,
            "job": {
                "title": row[5],
                "location": row[6],
                "company": row[7] or "Unknown",
                "source": row[9],
            },
            "error_message": None,
            "resume": None,
        })

    return {"data": applications, "total": total, "page": (offset // limit) + 1, "page_size": limit}


@router.get("/{application_id}")
async def get_application(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Get detailed status of a specific application."""
    row = db.execute(
        text("""
            SELECT a.id, a.job_posting_id, a.status, a.method,
                   a.screenshot_before, a.screenshot_after,
                   a.confirmation_id,
                   a.applied_at,
                   jp.title, jp.location, jp.url, c.name as company_name
            FROM applications a
            JOIN job_postings jp ON a.job_posting_id = jp.id
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE a.id = :aid AND a.user_id = :uid
        """),
        {"aid": _to_uuid(application_id), "uid": _to_uuid(user_id)},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    return {
        "id": str(row[0]),
        "job_posting_id": str(row[1]),
        "status": row[2],
        "method": row[3],
        "screenshot_before": row[4],
        "screenshot_after": row[5],
        "confirmation_id": row[6],
        "applied_at": row[7].isoformat() if row[7] else None,
        "job": {
            "title": row[8],
            "location": row[9],
            "url": row[10],
            "company": row[11] or "Unknown",
        },
    }


@router.get("/stats")
async def application_stats(user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Get aggregate application statistics."""
    stats = db.execute(
        text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'submitted') as submitted,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                COUNT(*) FILTER (WHERE status = 'replied') as replied,
                COUNT(*) FILTER (WHERE status = 'interview') as interview,
                COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
                COUNT(*) FILTER (WHERE status = 'accepted') as accepted
            FROM applications
            WHERE user_id = :uid
        """),
        {"uid": _to_uuid(user_id)},
    ).fetchone()

    return {
        "total": stats[0] or 0,
        "submitted": stats[1] or 0,
        "in_progress": stats[2] or 0,
        "replied": stats[3] or 0,
        "interview": stats[4] or 0,
        "rejected": stats[5] or 0,
        "accepted": stats[6] or 0,
    }
