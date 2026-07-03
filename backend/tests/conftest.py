"""
Pytest configuration for CareerPilot backend tests.

Uses an in-memory SQLite database and monkeypatches each router's _get_db
helper so tests run without Postgres or Celery.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure backend package importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Provide a dummy DATABASE_URL so _get_db() helpers don't raise before we patch them.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("LLM_PROVIDER", "stub")
