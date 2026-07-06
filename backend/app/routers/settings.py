from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, select
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
    model_name: Optional[str] = "default"


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


def _mask_key(k: str) -> str:
    if not k:
        return "****"
    if len(k) <= 4:
        return "****"
    return "*" * (len(k) - 4) + k[-4:]


@router.get("/api")
async def get_api_keys(user_id: str = Depends(get_current_user_id), db: Session = Depends(_get_db)):
    """Return the active system API keys (masked)."""
    from ..models import ApiSettings

    stmt = select(ApiSettings).where(ApiSettings.is_active.is_(True))
    rows = db.execute(stmt).scalars().all()
    keys = [
        {
            "provider": r.provider,
            "model_name": r.model_name,
            "key": _mask_key(r.api_key),
        }
        for r in rows
    ]
    return {"api_keys": keys}


@router.put("/api")
async def update_api_key(
    data: ApiKeyUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
):
    """Store or update a system API key for a given provider (+ optional model)."""
    from ..models import ApiSettings

    model_name = data.model_name or "default"
    stmt = select(ApiSettings).where(
        ApiSettings.provider == data.provider,
        ApiSettings.model_name == model_name,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        existing.api_key = data.key
        existing.is_active = True
    else:
        obj = ApiSettings(
            provider=data.provider,
            model_name=model_name,
            api_key=data.key,
            is_active=True,
        )
        db.add(obj)
    db.commit()
    return {"message": f"API key for {data.provider}/{model_name} updated"}


@router.delete("/api/{provider}")
async def delete_api_key(
    provider: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(_get_db),
    model_name: Optional[str] = None,
):
    """Deactivate the active system API key for a given provider (soft delete)."""
    from ..models import ApiSettings

    stmt = select(ApiSettings).where(
        ApiSettings.provider == provider,
        ApiSettings.is_active.is_(True),
    )
    if model_name:
        stmt = stmt.where(ApiSettings.model_name == model_name)
    existing = db.execute(stmt).scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail=f"No active API key found for {provider}")
    existing.is_active = False
    db.commit()
    return {"message": f"API key for {provider} deactivated"}
