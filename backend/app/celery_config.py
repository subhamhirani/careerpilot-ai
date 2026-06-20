"""
CareerPilot AI — Celery App Configuration.

Configures the Celery worker and Celery Beat schedule for periodic tasks.
All schedule times are expressed in IST (UTC+5:30).
"""

from __future__ import annotations

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Broker / Backend
# ---------------------------------------------------------------------------

BROKER_DEFAULT: str = "redis://redis:6379/0"
RESULT_DEFAULT: str = "redis://redis:6379/1"

BROKER_URL: str = os.getenv("CELERY_BROKER_URL", BROKER_DEFAULT)
RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", RESULT_DEFAULT)

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = Celery(
    "careerpilot",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.tasks", "app.tasks_resume", "app.tasks_scraper"],
)

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# ---------------------------------------------------------------------------
# Celery Beat Schedule (times in UTC; IST = UTC + 5:30)
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    "discover-jobs": {
        "task": "app.tasks.discover_jobs",
        "schedule": crontab(
            hour=int(os.getenv("CELERY_BEAT_DISCOVERY_HOUR", "2")),
            minute=int(os.getenv("CELERY_BEAT_DISCOVERY_MINUTE", "30")),
        ),
        "options": {"expires": 300},
    },
    "send-digest": {
        "task": "app.tasks.send_digest",
        "schedule": crontab(
            hour=int(os.getenv("CELERY_BEAT_DIGEST_HOUR", "3")),
            minute=int(os.getenv("CELERY_BEAT_DIGEST_MINUTE", "30")),
        ),
        "options": {"expires": 300},
    },
    "send-application-reminder": {
        "task": "app.tasks.send_application_reminder",
        "schedule": crontab(
            hour=int(os.getenv("CELERY_BEAT_REMINDER_HOUR", "4")),
            minute=int(os.getenv("CELERY_BEAT_REMINDER_MINUTE", "30")),
        ),
        "options": {"expires": 300},
    },
    "scrape-and-store-jobs": {
        "task": "app.tasks_scraper.scrape_and_store_jobs",
        "schedule": crontab(
            hour=int(os.getenv("CELERY_BEAT_SCRAPE_HOUR", "2")),
            minute=int(os.getenv("CELERY_BEAT_SCRAPE_MINUTE", "30")),
        ),
        "options": {"expires": 600},
    },
}

# ---------------------------------------------------------------------------
# Debug task (used to verify the worker is running)
# ---------------------------------------------------------------------------


@app.task(bind=True, max_retries=3)
def debug_task(self) -> str:
    """Simple debug task to verify Celery is working."""
    return f"Request: {self.request!r}"
