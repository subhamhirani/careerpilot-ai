"""
CareerPilot AI — Celery Task Definitions.

Wires agent functions into Celery tasks so that the Beat scheduler
can invoke them on a cron schedule.
All tasks are idempotent and safe to re-run.
"""

from __future__ import annotations

import logging
import os

from celery import current_app as celery_app
from tenacity import retry, stop_after_attempt, wait_exponential

from .agents import run_all_sources
from .agents.job_matching import run_job_matching_task

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry policy for all tasks
# ---------------------------------------------------------------------------

_task_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    name="app.tasks.discover_jobs",
)
def discover_jobs(self) -> dict:
    """Run all job scrapers and store new postings.

    Called by Celery Beat every morning at 8:00 AM IST.
    """
    logger.info("Task [discover_jobs] started")
    try:
        query = os.getenv("JOB_DISCOVERY_QUERY", "software engineer")
        result = run_all_sources(query)
        logger.info("Task [discover_jobs] completed: %s", result)
        return result
    except Exception as exc:
        logger.exception("Task [discover_jobs] failed")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    name="app.tasks.send_digest",
)
def send_digest(self) -> dict:
    """Collect today's top matches and dispatch the daily Telegram digest.

    Called by Celery Beat at 9:00 AM IST.
    """
    logger.info("Task [send_digest] started")
    try:
        result = {"matched": 0, "digest_dispatched": False}

        # Fetch user profiles + unscored jobs from DB
        try:
            from sqlalchemy import create_engine, select, text
            from sqlalchemy.orm import Session

            dsn = os.getenv("DATABASE_URL", "")
            sync_dsn = dsn.replace("+asyncpg", "+psycopg2")
            engine = create_engine(sync_dsn)

            with Session(engine) as session:
                # Fetch active user profiles
                profiles = session.execute(
                    text("SELECT user_id, skills, experience, preferred_roles FROM user_profiles")
                ).mappings().all()

                # Fetch unscored active job postings
                jobs = session.execute(
                    text("SELECT id, title, description, skills_required, location FROM job_postings WHERE is_active = true")
                ).mappings().all()

            if profiles and jobs:
                # Convert to dict format expected by matcher
                profile_dicts = [dict(p) for p in profiles]
                job_dicts = [dict(j) for j in jobs]

                from .agents.job_matching import run_job_matching_task, store_match_scores
                match_result = run_job_matching_task(profile_dicts, job_dicts, dsn=dsn)
                logger.info("Job matching done: %s", match_result)
                result["matched"] = len(match_result)
            else:
                logger.info("No profiles or jobs to match (profiles=%d, jobs=%d)", len(profiles), len(jobs))
        except Exception as db_err:
            logger.warning("DB query for matching failed (no data yet?): %s", db_err)

        # Then send digest via Telegram
        try:
            from .bot import send_daily_digest
            send_daily_digest.delay()
        except Exception as bot_err:
            logger.warning("Digest dispatch warning: %s", bot_err)

        result["digest_dispatched"] = True
        return result
    except Exception as exc:
        logger.exception("Task [send_digest] failed")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    name="app.tasks.send_application_reminder",
)
def send_application_reminder(self) -> dict:
    """Remind the user about pending approvals older than 48 hours.

    Called by Celery Beat at 10:00 AM IST.
    """
    logger.info("Task [send_application_reminder] started")
    try:
        from datetime import datetime, timezone, timedelta
        from .bot import send_pending_reminder

        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        send_pending_reminder.delay(cutoff_iso=cutoff.isoformat())

        logger.info("Task [send_application_reminder] completed")
        return {"reminded": True, "cutoff": cutoff.isoformat()}
    except Exception as exc:
        logger.exception("Task [send_application_reminder] failed")
        raise self.retry(exc=exc)
