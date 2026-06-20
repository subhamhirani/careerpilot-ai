# CareerPilot AI — Project Context & Status

## System Overview
CareerPilot AI is a multi-agent job search/application platform using FastAPI + Next.js 14 + Docker Compose with PostgreSQL/pgvector.

## Architecture
- **Backend**: FastAPI at `backend/app/` — port 7899
- **Frontend**: Next.js 14 at `frontend/src/` — port 3000
- **Database**: PostgreSQL + pgvector — port 5432
- **Cache/Queue**: Redis — port 6379
- **Worker**: Celery worker for background tasks
- **Beat**: Celery beat for scheduled tasks
- **Proxy**: Caddy — ports 80/443
- **Monitor**: Uptime Kuma — port 3001

## Key Files

### Backend
- `backend/app/main.py` — FastAPI app entry, router registration
- `backend/app/models.py` — SQLAlchemy ORM models (User, Resume, JobPosting, MatchScore, Application, etc.)
- `backend/app/auth.py` — JWT auth, password hashing, TOTP
- `backend/app/celery_config.py` — Celery app configuration
- `backend/app/tasks.py` — Celery tasks (discover_jobs, send_digest, send_application_reminder)
- `backend/app/tasks_resume.py` — Resume processing pipeline task
- `backend/app/state.py` — In-memory state stores
- `backend/app/routers/auth.py` — Auth endpoints (register, login, me, refresh, totp)
- `backend/app/routers/jobs.py` — Jobs CRUD endpoints
- `backend/app/routers/matches.py` — Match scores endpoints
- `backend/app/routers/applications.py` — Applications endpoints
- `backend/app/routers/approvals.py` — Approval flow endpoints
- `backend/app/routers/resumes.py` — Resume upload/management
- `backend/app/routers/process_status.py` — Process monitoring endpoints
- `backend/app/routers/settings.py` — User settings + API key management
- `backend/app/routers/dashboard.py` — Dashboard stats + analytics
- `backend/app/agents/job_discovery.py` — LinkedIn, Naukri, Indeed scrapers
- `backend/app/agents/application.py` — Playwright-based application submitter
- `backend/app/agents/job_matching.py` — Job matching agent
- `backend/app/agents/resume_analysis.py` — Resume parsing agent

### Frontend
- `frontend/src/lib/api.ts` — API client with auth token management
- `frontend/src/lib/auth-context.tsx` — Auth context provider
- `frontend/src/app/page.tsx` — Dashboard page
- `frontend/src/app/processes/page.tsx` — Live process monitoring
- `frontend/src/app/settings/page.tsx` — Settings page (general, search, notifications)
- `frontend/src/components/sidebar.tsx` — Navigation sidebar

## Database Schema
- **users** — id, email, hashed_password, totp_secret, created_at
- **user_profiles** — id, user_id, full_name, phone, summary, skills, experience, education, raw_json
- **resumes** — id, user_id, title, file_path, file_type, parsed_text, is_active, created_at
- **companies** — id, name, website, industry
- **job_postings** — id, company_id, title, description, location, url, source, salary_min, salary_max, posted_at, discovered_at, hash_key, is_duplicate, status, embedding
- **match_scores** — id, user_id, job_posting_id, score, tier, reasons_json, missing_skills_json, risk_indicators_json, computed_at
- **applications** — id, user_id, job_posting_id, status, method, screenshot_before, screenshot_after, confirmation_id, error_message
- **pending_approvals** — id, user_id, entity_type, entity_id, status, match_score, created_at, decided_at
- **process_statuses** — id, user_id, task_name, status, progress_pct, current_step, error_message
- **api_settings** — id, user_id, provider_name, api_key
- **search_preferences** — id, user_id, keywords, locations, etc.

## API Routes (all under /api prefix)
- POST /auth/register — Register new user
- POST /auth/login — Login (now with DB fallback)
- GET /auth/me — Get current user
- POST /auth/refresh — Refresh token
- GET /resumes/ — List resumes
- POST /resumes/upload — Upload resume (multipart/form-data, field: "file")
- GET /resumes/{id} — Get resume details
- DELETE /resumes/{id} — Delete resume
- GET /jobs/ — List job postings (with filters)
- GET /jobs/{id} — Get job details with match score
- POST /jobs/{id}/save — Save job
- POST /jobs/{id}/reject — Reject job
- GET /matches/ — List match scores
- GET /matches/{id} — Get match details
- POST /matches/re-rank — Trigger re-ranking
- GET /applications/ — List applications
- GET /applications/{id} — Get application details
- GET /applications/stats — Application statistics
- GET /approvals/ — List pending approvals
- POST /approvals/{id}/approve — Approve application
- POST /approvals/{id}/reject — Reject application
- GET /process-statuses/ — List process statuses
- GET /settings/ — Get user settings
- PUT /settings/ — Update user settings
- GET /settings/api — Get API keys (masked)
- PUT /settings/api — Store/update API key
- DELETE /settings/api/{provider} — Delete API key
- GET /dashboard/stats — Dashboard statistics
- GET /analytics — Analytics data
- GET /health — Health check

## Key Fixes Applied (2026-06-20)
1. **docker-compose.yml** — Separate backend/worker/beat services, shared storage volume
2. **auth.py** — DB-backed login fallback, registration fails if DB insert fails
3. **tasks_resume.py** — Fixed JSONB parameter casting for psycopg2
4. **celery_config.py** — Fixed include list (app.tasks_resume)
5. **All routers** — Now query PostgreSQL instead of returning hardcoded empty results
6. **Dashboard** — Real DB queries for stats
7. **Settings** — API key management with PostgreSQL storage

## Known Issues
- Job scraping (LinkedIn/Naukri) may fail due to anti-scraping — expected
- Indeed scraper is a stub (needs API key or proxy)
- Playwright installed but chromium may need separate install
- Worker/beat containers show "unhealthy" (no healthcheck defined) — cosmetic

## GitHub
- Repo: https://github.com/subhamhirani/careerpilot-ai (private)
- User: subhamhirani
- Latest commit: 603fde7

## Environment
- Ubuntu 26.04 LTS (AWS)
- Python 3.11.15
- Node.js (Next.js 14)
- Docker Compose with 8 services
