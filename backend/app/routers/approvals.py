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


def _to_uuid(value) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


@router.get("/")
async def list_pending_approvals(
    status: str | None = "pending",
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """List all pending approvals awaiting user action."""
    uid = _to_uuid(user_id)
    conditions = ["pa.user_id = :uid"]
    params = {"uid": uid, "limit": limit, "offset": offset}

    if status:
        conditions.append("pa.status = :status")
        params["status"] = status

    where = " AND ".join(conditions)

    count_sql = f"SELECT COUNT(*) FROM pending_approvals pa WHERE {where}"
    total = db.execute(text(count_sql), params).scalar() or 0

    rows = db.execute(
        text(f"""
            SELECT pa.id, pa.entity_type, pa.entity_id, pa.status,
                   pa.created_at,
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
            "job_title": row[5],
            "job_location": row[6],
            "company": row[7] or "Unknown",
        })

    return {"approvals": approvals, "total": total, "limit": limit, "offset": offset}


@router.post("/{approval_id}/approve")
async def approve_application(
    approval_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Approve an application and trigger submission."""
    uid = _to_uuid(user_id)

    # Update approval status
    result = db.execute(
        text("""
            UPDATE pending_approvals
            SET status = 'approved', reviewed_at = NOW()
            WHERE id = :aid AND user_id = :uid AND status = 'PENDING'
            RETURNING entity_id, entity_type
        """),
        {"aid": _to_uuid(approval_id), "uid": uid},
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Approval not found or already processed")

    # Create application record
    job_id = str(result[0])
    app_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO applications (id, user_id, job_posting_id, status, method)
            VALUES (:aid, :uid, :jid, 'draft', 'automated')
        """),
        {"aid": app_id, "uid": uid, "jid": job_id},
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
            SET status = 'rejected', reviewed_at = NOW()
            WHERE id = :aid AND user_id = :uid AND status = 'PENDING'
        """),
        {"aid": _to_uuid(approval_id), "uid": _to_uuid(user_id)},
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Approval not found or already processed")

    db.commit()
    return {"status": "rejected", "approval_id": approval_id}
