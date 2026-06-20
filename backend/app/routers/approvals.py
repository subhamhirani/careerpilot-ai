"""
CareerPilot AI — Approvals API Router.

Endpoints for reviewing and acting on pending application approvals.
"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..auth import get_current_user_id

router = APIRouter(prefix="/approvals", tags=["approvals"])


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
async def list_pending_approvals(
    status: str | None = "pending",
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """List all pending approvals awaiting user action."""
    conditions = ["pa.user_id = :uid"]
    params = {"uid": uuid.UUID(user_id), "limit": limit, "offset": offset}

    if status:
        conditions.append("pa.status = :status")
        params["status"] = status

    where = " AND ".join(conditions)

    count_sql = f"SELECT COUNT(*) FROM pending_approvals pa WHERE {where}"
    total = db.execute(text(count_sql), params).scalar() or 0

    rows = db.execute(
        text(f"""
            SELECT pa.id, pa.entity_type, pa.entity_id, pa.status,
                   pa.created_at, pa.match_score,
                   jp.title, jp.location, c.name as company_name
            FROM pending_approvals pa
            LEFT JOIN job_postings jp ON pa.entity_id = jp.id
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE {where}
            ORDER BY pa.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).fetchall()

    approvals = []
    for row in rows:
        approvals.append({
            "id": str(row[0]),
            "entity_type": row[1],
            "entity_id": str(row[2]),
            "status": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "match_score": row[5],
            "job_title": row[6],
            "job_location": row[7],
            "company": row[8] or "Unknown",
        })

    return {"approvals": approvals, "total": total, "limit": limit, "offset": offset}


@router.post("/{approval_id}/approve")
async def approve_application(
    approval_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Approve an application and trigger submission."""
    # Update approval status
    result = db.execute(
        text("""
            UPDATE pending_approvals
            SET status = 'approved', decided_at = NOW()
            WHERE id = :aid AND user_id = :uid AND status = 'pending'
            RETURNING entity_id, entity_type
        """),
        {"aid": approval_id, "uid": uuid.UUID(user_id)},
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Approval not found or already processed")

    # Create application record
    job_id = str(result[0])
    app_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO applications (id, user_id, job_posting_id, status, method)
            VALUES (:aid, :uid, :jid, 'pending', 'automated')
        """),
        {"aid": app_id, "uid": uuid.UUID(user_id), "jid": job_id},
    )
    db.commit()

    return {
        "status": "approved",
        "approval_id": approval_id,
        "application_id": app_id,
        "message": "Application submission queued",
    }


@router.post("/{approval_id}/reject")
async def reject_application(
    approval_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Reject an application."""
    result = db.execute(
        text("""
            UPDATE pending_approvals
            SET status = 'rejected', decided_at = NOW()
            WHERE id = :aid AND user_id = :uid AND status = 'pending'
        """),
        {"aid": approval_id, "uid": uuid.UUID(user_id)},
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Approval not found or already processed")

    db.commit()
    return {"status": "rejected", "approval_id": approval_id}
