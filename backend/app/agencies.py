"""
CareerPilot AI — Database Connection Management.

Provides an async connection pool (asyncpg) and a helper to run SQL
queries.  Use the ORM models (app.models) for day-to-day operations;
use this module for raw SQL, batch operations, or embedding search
via pgvector.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from dotenv import load_dotenv
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

load_dotenv()

# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://careerpilot:careerpilot@localhost:5432/careerpilot",
)

# Parse the async URL into a plain asyncpg DSN
_DSN: str = DATABASE_URL.replace("+asyncpg", "")

_MIN_POOL_SIZE: int = int(os.getenv("DB_POOL_MIN", "2"))
_MAX_POOL_SIZE: int = int(os.getenv("DB_POOL_MAX", "10"))

# ──────────────────────────────────────────────
#  Global pool reference
# ──────────────────────────────────────────────

_pool: Any = None  # asyncpg.Pool


async def get_pool() -> Any:
    """Return the global asyncpg connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        import asyncpg

        _pool = await asyncpg.create_pool(
            dsn=_DSN,
            min_size=_MIN_POOL_SIZE,
            max_size=_MAX_POOL_SIZE,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    """Close the global connection pool (call during app shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ──────────────────────────────────────────────
#  Connection context manager
# ──────────────────────────────────────────────


@asynccontextmanager
async def get_connection() -> AsyncGenerator[Any, None]:
    """Yield a single connection from the pool.

    Usage::

        async with get_connection() as conn:
            rows = await conn.fetch("SELECT * FROM users")
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


# ──────────────────────────────────────────────
#  Query helpers
# ──────────────────────────────────────────────


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True,
)
async def fetch_all(
    query: str,
    *args: Any,
    timeout: Optional[float] = 30.0,
) -> list[Any]:
    """Execute a raw SQL query and return all matching rows.

    Retries up to 3 times with exponential back-off on connection errors.
    """
    async with get_connection() as conn:
        return await conn.fetch(query, *args, timeout=timeout)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True,
)
async def fetch_one(
    query: str,
    *args: Any,
    timeout: Optional[float] = 30.0,
) -> Optional[Any]:
    """Execute a raw SQL query and return the first row (or ``None``)."""
    async with get_connection() as conn:
        return await conn.fetchrow(query, *args, timeout=timeout)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True,
)
async def execute(
    query: str,
    *args: Any,
    timeout: Optional[float] = 30.0,
) -> str:
    """Execute a raw SQL statement (INSERT/UPDATE/DELETE).

    Returns the command status tag (e.g. ``INSERT 0 1``).
    """
    async with get_connection() as conn:
        return await conn.execute(query, *args, timeout=timeout)


# ──────────────────────────────────────────────
#  Embedding search helper (pgvector)
# ──────────────────────────────────────────────

async def similarity_search(
    table: str,
    embedding_column: str,
    query_embedding: list[float],
    limit: int = 10,
    threshold: float = 0.5,
    extra_where: Optional[str] = None,
) -> list[Any]:
    """Perform a cosine-similarity search using pgvector's ``<=>`` operator.

    Args:
        table: The table name (e.g. ``job_postings``).
        embedding_column: The VECTOR column name.
        query_embedding: A 384-dimensional float vector.
        limit: Maximum results.
        threshold: Minimum cosine-distance threshold (lower = more similar).
        extra_where: Optional additional WHERE clause (without the ``WHERE`` keyword).

    Returns:
        List of asyncpg ``Record`` objects.
    """
    embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"
    sql = (
        f"SELECT *, ({embedding_column} <=> '{embedding_literal}'::vector) AS distance "
        f"FROM {table} "
        f"WHERE ({embedding_column} <=> '{embedding_literal}'::vector) <= {threshold} "
    )
    if extra_where:
        sql += f" AND {extra_where} "
    sql += f"ORDER BY distance ASC LIMIT {limit}"

    return await fetch_all(sql)
