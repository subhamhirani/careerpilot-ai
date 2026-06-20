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


@router.get("/")
async def list_applications(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """List all submitted applications with status tracking."""
    conditions = ["a.user_id = :uid"]
    params = {"uid": uuid.UUID(user_id), "limit": limit, "offset": offset}

    if status:
        conditions.append("a.status = :status")
        params["status"] = status

    where = " AND ".join(conditions)

    count_sql = f"SELECT COUNT(*) FROM applications a WHERE {where}"
    total = db.execute(text(count_sql), params).scalar() or 0

    rows = db.execute(
        text(f"""
            SELECT a.id, a.job_posting_id, a.status, a.method,
                   a.created_at, a.updated_at,
                   jp.title, jp.location, c.name as company_name
            FROM applications a
            JOIN job_postings jp ON a.job_posting_id = jp.id
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE {where}
            ORDER BY a.created_at DESC
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
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
            "job_title": row[6],
            "job_location": row[7],
            "company": row[8] or "Unknown",
        })

    return {"applications": applications, "total": total, "limit": limit, "offset": offset}


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
                   a.confirmation_id, a.error_message,
                   a.created_at, a.updated_at,
                   jp.title, jp.location, jp.url, c.name as company_name
            FROM applications a
            JOIN job_postings jp ON a.job_posting_id = jp.id
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE a.id = :aid AND a.user_id = :uid
        """),
        {"aid": application_id, "uid": uuid.UUID(user_id)},
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
        "error_message": row[7],
        "created_at": row[8].isoformat() if row[8] else None,
        "updated_at": row[9].isoformat() if row[9] else None,
        "job": {
            "title": row[10],
            "location": row[11],
            "url": row[12],
            "company": row[13] or "Unknown",
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
        {"uid": uuid.UUID(user_id)},
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
