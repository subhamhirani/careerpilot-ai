from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from ..auth import get_current_user_id

router = APIRouter(prefix="/settings", tags=["settings"])


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


class ApiKeyUpdate(BaseModel):
    provider: str
    key: str


@router.get("")
async def get_settings(user_id: str = Depends(get_current_user_id)):
    """Return the current user's settings, or sensible defaults."""
    return {
        "notification_enabled": True,
        "auto_apply": False,
        "max_applications_per_day": 5,
        "search_queries": [],
    }


@router.put("")
async def update_settings(
    body: dict,
    user_id: str = Depends(get_current_user_id),
):
    """Update the current user's settings (partial update)."""
    current = {
        "notification_enabled": True,
        "auto_apply": False,
        "max_applications_per_day": 5,
        "search_queries": [],
    }
    allowed = {"notification_enabled", "auto_apply", "max_applications_per_day", "search_queries"}
    for key in allowed:
        if key in body:
            current[key] = body[key]
    return current


@router.get("/api")
async def get_api_keys(user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Return the current user's configured API keys (masked)."""
    from ..models import ApiSettings
    stmt = select(ApiSettings).where(ApiSettings.user_id == uuid.UUID(user_id))
    results = db.execute(stmt).scalars().all()
    keys = []
    for r in results:
        # Mask the key - show only last 4 chars
        masked = "*" * (len(r.api_key) - 4) + r.api_key[-4:] if len(r.api_key) > 4 else "****"
        keys.append({"provider": r.provider_name, "key": masked})
    return {"api_keys": keys}


@router.put("/api")
async def update_api_key(data: ApiKeyUpdate, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Store or update an API key for a given provider."""
    from ..models import ApiSettings
    # Check if key already exists for this provider
    stmt = select(ApiSettings).where(
        ApiSettings.user_id == uuid.UUID(user_id),
        ApiSettings.provider_name == data.provider,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        existing.api_key = data.key
    else:
        obj = ApiSettings(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            provider_name=data.provider,
            api_key=data.key,
        )
        db.add(obj)
    db.commit()
    return {"message": f"API key for {data.provider} updated"}


@router.delete("/api/{provider}")
async def delete_api_key(provider: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Delete an API key for a given provider."""
    from ..models import ApiSettings
    stmt = select(ApiSettings).where(
        ApiSettings.user_id == uuid.UUID(user_id),
        ApiSettings.provider_name == provider,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail=f"No API key found for {provider}")
    db.delete(existing)
    db.commit()
    return {"message": f"API key for {provider} deleted"}
