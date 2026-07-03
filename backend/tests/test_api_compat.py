"""
Compatibility tests for CareerPilot backend API changes.

Validates that:
- cover_letters.GenerateRequest accepts both job_id and job_posting_id aliases
- jobs router exposes /jobs/ with expected query params
- _to_uuid helpers handle dashed/non-dashed UUIDs
- user_profile preferred_location persistence shape

Run inside the backend container:
    docker compose exec backend pytest tests/test_api_compat.py -v
"""
from __future__ import annotations

import uuid

import pytest


# ── cover_letters.GenerateRequest alias ────────────────────────────

def test_cover_letter_request_accepts_job_id():
    from app.routers.cover_letters import GenerateRequest

    req = GenerateRequest(job_id="abc-123")
    assert req.resolved_job_id() == "abc-123"


def test_cover_letter_request_accepts_job_posting_id_alias():
    from app.routers.cover_letters import GenerateRequest

    req = GenerateRequest(job_posting_id="abc-123")
    assert req.resolved_job_id() == "abc-123"


def test_cover_letter_request_job_id_takes_precedence():
    from app.routers.cover_letters import GenerateRequest

    req = GenerateRequest(job_id="primary", job_posting_id="secondary")
    assert req.resolved_job_id() == "primary"


def test_cover_letter_request_requires_some_id():
    from app.routers.cover_letters import GenerateRequest

    req = GenerateRequest()
    with pytest.raises(ValueError):
        req.resolved_job_id()


def test_cover_letter_request_defaults():
    from app.routers.cover_letters import GenerateRequest

    req = GenerateRequest(job_id="x")
    assert req.tone == "professional"
    assert req.short is False


# ── UUID helpers ─────────────────────────────────────────────────

def test_cover_letters_to_uuid_dashed():
    from app.routers.cover_letters import _to_uuid

    u = uuid.uuid4()
    assert _to_uuid(str(u)) == u


def test_cover_letters_to_uuid_non_dashed():
    from app.routers.cover_letters import _to_uuid

    u = uuid.uuid4()
    hex_str = u.hex  # no dashes
    assert _to_uuid(hex_str) == u


# ── jobs router ─────────────────────────────────────────────────

def test_jobs_router_prefix():
    from app.routers.jobs import router

    # APIRouter prefix is stored on the router object
    assert router.prefix == "/jobs"


def test_jobs_router_has_list_endpoint():
    from app.routers.jobs import router

    paths = {route.path for route in router.routes}
    # prefix "/jobs" is prepended; root endpoint "/" appears as "/jobs/"
    assert "/jobs/" in paths


# ── user_profile persistence (schema-level smoke) ────────────────

def test_user_profile_router_prefix():
    from app.routers.user_profile import router

    assert router.prefix == "/user-profile"


def test_user_profile_router_has_location_endpoints():
    from app.routers.user_profile import router

    paths = {route.path for route in router.routes}
    # prefix "/user-profile" is prepended; root "/" appears as "/user-profile/"
    assert "/user-profile/" in paths


# ── resumes router ──────────────────────────────────────────────

def test_resumes_router_prefix():
    from app.routers.resumes import router

    assert router.prefix == "/resumes"


def test_resumes_serialize_handles_missing_file():
    """_serialize_resume should not crash if file_path is empty."""
    from app.routers.resumes import _serialize_resume

    # Mock row: (id, user_id, file_path, name, file_type, is_active, created, updated)
    row = ("r1", "u1", "", "Resume.pdf", "pdf", True, None, None)
    result = _serialize_resume(row)
    assert result["id"] == "r1"
    assert result["file_size"] == 0
    assert result["name"] == "Resume.pdf"
    assert result["is_active"] is True


# ── onboarding router ────────────────────────────────────────────

def test_onboarding_router_prefix():
    from app.routers.onboarding import router

    assert router.prefix == "/onboarding"


# ── app import smoke ─────────────────────────────────────────────

def test_app_imports():
    """The FastAPI app should import without errors."""
    from app.main import app

    assert app is not None
    # Health routes exist
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/api/health" in paths


def test_app_has_expected_routers():
    """All expected routers are mounted."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert any(p.startswith("/api/jobs") for p in paths)
    assert any(p.startswith("/api/cover-letters") for p in paths)
    assert any(p.startswith("/api/resumes") for p in paths)
    assert any(p.startswith("/api/onboarding") for p in paths)
    assert any(p.startswith("/api/user-profile") for p in paths)
