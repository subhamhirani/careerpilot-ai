"""CareerPilot AI — Process Status API Router.

Provides CRUD endpoints for process status monitoring.
"""

from __future__ import annotations

import uuid
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..models import ProcessStatus

router = APIRouter(prefix="/process-statuses", tags=["process-statuses"])


# Pydantic models
class ProcessStatusBase(BaseModel):
    task_name: str = Field(..., max_length=255)
    status: Optional[str] = Field(None, max_length=64)  # queued, running, completed, failed
    progress_pct: Optional[int] = Field(None, ge=0, le=100)
    current_step: Optional[str] = Field(None, max_length=255)
    error_message: Optional[str] = None


class ProcessStatusCreate(ProcessStatusBase):
    pass


class ProcessStatusUpdate(ProcessStatusBase):
    pass


class ProcessStatusResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    task_name: str
    status: str
    progress_pct: int = 0
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def get_db():
    """Yield a SQLAlchemy session (same pattern as tasks.py)."""
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


@router.get("", response_model=List[ProcessStatusResponse])
def list_process_statuses(
    task_name: Optional[str] = Query(None, description="Filter by task name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List process statuses for the current user."""
    stmt = select(ProcessStatus).where(ProcessStatus.user_id == user_id)
    if task_name:
        stmt = stmt.where(ProcessStatus.task_name == task_name)
    if status:
        stmt = stmt.where(ProcessStatus.status == status)
    stmt = stmt.offset(offset).limit(limit).order_by(ProcessStatus.created_at.desc())
    results = db.execute(stmt).scalars().all()
    return results


@router.post("", response_model=ProcessStatusResponse, status_code=status.HTTP_201_CREATED)
def create_process_status(
    payload: ProcessStatusCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create a new process status entry."""
    obj = ProcessStatus(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        task_name=payload.task_name,
        status=payload.status or "queued",
        progress_pct=payload.progress_pct or 0,
        current_step=payload.current_step,
        error_message=payload.error_message,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{process_id}", response_model=ProcessStatusResponse)
def get_process_status(
    process_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get a specific process status by ID."""
    stmt = select(ProcessStatus).where(
        ProcessStatus.id == process_id,
        ProcessStatus.user_id == user_id,
    )
    try:
        result = db.execute(stmt).scalar_one()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Process status not found")
    return result


@router.patch("/{process_id}", response_model=ProcessStatusResponse)
def update_process_status(
    process_id: uuid.UUID,
    payload: ProcessStatusUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update a process status entry."""
    stmt = select(ProcessStatus).where(
        ProcessStatus.id == process_id,
        ProcessStatus.user_id == user_id,
    )
    try:
        obj = db.execute(stmt).scalar_one()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Process status not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obj, field, value)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_process_status(
    process_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Delete a process status entry."""
    stmt = select(ProcessStatus).where(
        ProcessStatus.id == process_id,
        ProcessStatus.user_id == user_id,
    )
    try:
        obj = db.execute(stmt).scalar_one()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Process status not found")
    db.delete(obj)
    db.commit()
    return None