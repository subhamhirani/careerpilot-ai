"""
CareerPilot AI — Match Scores API Router.
"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..auth import get_current_user_id

router = APIRouter(prefix="/matches", tags=["matches"])


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
async def list_matches(
    tier: str | None = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """List match scores for the current user."""
    conditions = ["ms.user_id = :uid"]
    params = {"uid": uuid.UUID(user_id), "limit": limit, "offset": offset}

    if tier:
        conditions.append("ms.grade = :tier")
        params["tier"] = tier

    where = " AND ".join(conditions)

    count_sql = f"SELECT COUNT(*) FROM match_scores ms WHERE {where}"
    total = db.execute(text(count_sql), params).scalar() or 0

    rows = db.execute(
        text(f"""
            SELECT ms.id, ms.job_posting_id, ms.overall_score, ms.grade,
                   ms.details, ms.created_at,
                   jp.title, jp.location, c.name as company_name
            FROM match_scores ms
            JOIN job_postings jp ON ms.job_posting_id = jp.id
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE {where}
            ORDER BY ms.overall_score DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).fetchall()

    matches = []
    for row in rows:
        details = row[4]
        if isinstance(details, str):
            import json as _json
            details = _json.loads(details)
        if not isinstance(details, dict):
            details = {}
        matches.append({
            "id": str(row[0]),
            "job_posting_id": str(row[1]),
            "score": row[2],
            "tier": row[3],
            "reasons": details.get("matched_skills", []),
            "missing_skills": details.get("missing_skills", []),
            "computed_at": row[5].isoformat() if row[5] else None,
            "job_title": row[6],
            "job_location": row[7],
            "company": row[8] or "Unknown",
        })

    return {"matches": matches, "total": total, "limit": limit, "offset": offset}


@router.get("/{match_id}")
async def get_match(match_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Get detailed match breakdown."""
    row = db.execute(
        text("""
            SELECT ms.id, ms.job_posting_id, ms.overall_score, ms.grade,
                   ms.details,
                   ms.created_at, jp.title, jp.description, jp.location, jp.source_url,
                   c.name as company_name
            FROM match_scores ms
            JOIN job_postings jp ON ms.job_posting_id = jp.id
            LEFT JOIN companies c ON jp.company_id = c.id
            WHERE ms.id = :mid AND ms.user_id = :uid
        """),
        {"mid": match_id, "uid": uuid.UUID(user_id)},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Match not found")

    details = row[4]
    if isinstance(details, str):
        import json as _json
        details = _json.loads(details)
    if not isinstance(details, dict):
        details = {}

    return {
        "id": str(row[0]),
        "job_posting_id": str(row[1]),
        "score": row[2],
        "tier": row[3],
        "reasons": details.get("matched_skills", []),
        "missing_skills": details.get("missing_skills", []),
        "risk_indicators": details.get("risk_indicators", []),
        "computed_at": row[5].isoformat() if row[5] else None,
        "job": {
            "title": row[6],
            "description": row[7],
            "location": row[8],
            "url": row[9],
            "company": row[10] or "Unknown",
        },
    }


@router.post("/re-rank")
async def re_rank_matches(user_id: str = Depends(get_current_user_id)):
    """Trigger a re-ranking of all unmatched jobs."""
    try:
        from app.tasks import discover_jobs
        discover_jobs.delay()
    except Exception:
        pass
    return {"status": "re_rank_triggered", "message": "Re-ranking started"}
