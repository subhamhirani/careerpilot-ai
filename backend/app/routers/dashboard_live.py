"""
Public dashboard endpoint – aggregates live system health without requiring authentication.
Provides a quick snapshot for monitoring scrapers and overall job volume.
"""

from fastapi import APIRouter
from sqlalchemy import create_engine, text
import os, uuid, json

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def _get_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
    return create_engine(sync_dsn)

async def live_dashboard():
    """Return a small JSON payload with live system metrics.
    No authentication – suitable for status pages or health monitors.
    """
    engine = _get_db()
    try:
        with engine.connect() as conn:
            # Total number of job postings stored
            jobs_res = conn.execute(text("SELECT COUNT(*) FROM job_postings")).fetchone()
            jobs_total = jobs_res[0] if jobs_res else 0
            # Latest scrape timestamp (if scraper_status table exists)
            try:
                ts_res = conn.execute(text("SELECT MAX(scraped_at) FROM scraper_status")).fetchone()
                last_scrape = ts_res[0].isoformat() if ts_res and ts_res[0] else None
                # Whether a scraper run is currently marked as running
                run_res = conn.execute(text("SELECT is_running FROM scraper_status ORDER BY scraped_at DESC LIMIT 1")).fetchone()
                scraper_running = bool(run_res[0]) if run_res else False
            except Exception:
                # If the scraper_status table is missing, fallback gracefully
                last_scrape = None
                scraper_running = False
    finally:
        engine.dispose()
    return {
        "jobs_total": jobs_total,
        "scraper_running": scraper_running,
        "last_scrape": last_scrape,
    }

@router.get("/live", tags=["dashboard"])
async def live_alias():
    """Backward‑compatible alias for ``/live`` – returns the same payload as ``/stats``.
    """
    return await live_dashboard()
