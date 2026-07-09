"""
CareerPilot AI — Centralized Database Connection Pool & Session Management.

Provides a shared synchronous SQLAlchemy Engine with proper connection pool
configuration (pool_pre_ping, recycling, overflow limits) to avoid per-request
engine creation churn across routers and background tasks.
"""

from __future__ import annotations

import logging
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    """Return the global singleton sync SQLAlchemy engine with connection pooling."""
    global _engine
    if _engine is None:
        dsn = os.getenv("DATABASE_URL", "")
        if not dsn:
            raise RuntimeError("DATABASE_URL not set")
        sync_dsn = dsn.replace("+asyncpg", "+psycopg2")

        # Use connection pooling for non-memory databases
        if "sqlite" in sync_dsn:
            _engine = create_engine(sync_dsn)
        else:
            min_size = int(os.getenv("DB_POOL_MIN", "2"))
            max_size = int(os.getenv("DB_POOL_MAX", "10"))
            _engine = create_engine(
                sync_dsn,
                pool_size=min_size,
                max_overflow=max(0, max_size - min_size),
                pool_pre_ping=True,
                pool_recycle=3600,
            )
    return _engine


def get_session_factory() -> sessionmaker:
    """Return the global sessionmaker bound to the shared engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency generator yielding a database session from the pool."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def dispose_db() -> None:
    """Dispose the shared SQLAlchemy engine pool (call during app shutdown)."""
    global _engine, _SessionLocal
    if _engine is not None:
        logger.info("Disposing shared SQLAlchemy engine connection pool")
        _engine.dispose()
        _engine = None
        _SessionLocal = None
