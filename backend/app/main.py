"""
CareerPilot AI — FastAPI Application Entry Point.

Configures CORS, static file serving, routers, and a health check.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __app_name__, __version__
from .auth import get_current_user_id
from .routers import scraper, auth, resumes, jobs, matches, approvals, applications, dashboard, dashboard_live, settings, process_status, notifications, user_profile, resume_parsing, cover_letters, onboarding
from .routers.resumes import upload_resume
from .telemetry import log_event

# ── Provider auto‑registration ────────────────────────────
# Importing this package auto‑registers all built‑in providers
# into ProviderFactory so routers can use them via Dependency.
from app import providers  # noqa: F401

# ── Load .env before anything else ───────────────────────────
load_dotenv()


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    yield
    from .agencies import close_pool
    from .db import dispose_db

    await close_pool()
    dispose_db()


# ── App factory ──────────────────────────────────────────────

app = FastAPI(
    title=__app_name__,
    version=__version__,
    description="AI-powered career assistant backend",
    lifespan=lifespan,
)

# ── CORS (must be added BEFORE routers) ──────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://3.109.213.250,https://3.109.213.250,http://localhost:7899").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request logging middleware ────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    log_event("request", {"path": request.url.path, "method": request.method})
    return await call_next(request)

# ── Routers (order matters: more specific routes first) ──────
# onboarding before jobs so /onboarding/status doesn't match /jobs/{job_id}
# Provide explicit ``/api/onboarding`` endpoint (no trailing slash) to avoid 404s.
@app.get("/api/onboarding", tags=["onboarding"])
async def onboarding_root_noslash(user_id: str = Depends(get_current_user_id)):
    """Direct access to onboarding status without a trailing slash.

    Calls the same logic as ``onboarding.get_onboarding_status``.
    """
    return await onboarding.get_onboarding_status(user_id)

# Existing router includes still apply for ``/api/onboarding/`` and sub‑paths.
app.include_router(onboarding.router, prefix="/api")
# onboarding before jobs so /onboarding/status doesn't match /jobs/{job_id}
app.include_router(scraper.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(cover_letters.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(dashboard_live.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(process_status.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(user_profile.router, prefix="/api")
app.include_router(resume_parsing.router, prefix="/api")

# ── Static files ─────────────────────────────────────────────

static_dir = Path(os.getenv("STATIC_DIR", "./static")).resolve()
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Health check ─────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Basic health-check endpoint (no DB dependency)."""
    return {
        "status": "ok",
        "app": __app_name__,
        "version": __version__,
    }


@app.get("/api/health", tags=["system"])
async def api_health_check() -> dict:
    """Alias health check under /api prefix for Caddy proxy."""
    return {
        "status": "ok",
        "app": __app_name__,
        "version": __version__,
    }


@app.post("/api/resume/upload", tags=["resumes"])
async def upload_resume_singular(
    file: UploadFile = File(...),
    name: str = "",
    user_id: str = Depends(get_current_user_id),
):
    """Alias for /api/resumes/upload to support benchmark scripts."""
    return await upload_resume(file=file, name=name, user_id=user_id)


# ── Global exception handler ─────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all to avoid leaking stack traces in production."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
            "path": request.url.path,
        },
    )
