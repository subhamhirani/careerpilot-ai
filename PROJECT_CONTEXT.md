# CareerPilot AI — Project Context & Status

## System Overview
CareerPilot AI is a multi-agent job search/application platform using FastAPI + Next.js 14 + Docker Compose with PostgreSQL/pgvector.

## Architecture
- Backend: FastAPI at `backend/app/` — port 7899
- Frontend: Next.js 14 at `frontend/src/` — port 3000
- Database: PostgreSQL + pgvector — port 5432
- Cache/Queue: Redis — port 6379
- Celery Worker + Beat
- Caddy (Reverse Proxy for API + Frontend)
- Monitor: Uptime Kuma — port 3001

## Key Updates (June 20, 2026)
1. Paginated Job/Application endpoints implemented.
2. Job Application workflow (`/apply`) implemented.
3. Fixed `NEXT_PUBLIC_API_URL` to route correctly via Caddy proxy (`/api`).
4. Fixed Caddyfile routing issues (removed invalid `root` directive, fixed backend service aliasing).
5. Frontend dashboard live-load issues resolved.

## Key Updates (July 3, 2026)
1. Fixed location parameter usage in `backend/app/agents/multi_portal_scraper.py` to respect `selected_locations` parameter.
2. Fixed location parameter bug in `backend/app/config.py` (changed `==` to `!=` for environment check).
3. Ran test suite and fixed 3 failing tests (test_parse, test_validate, test_edge).
4. Updated project documentation: `PROJECT_CONTEXT.md` and `FULL_PROJECT_STATE.md`.
5. Committed and pushed fixes to GitHub (commit 6b9452d).
6. Deployed updated Docker Compose stack on AWS, restarting services.
7. **Fixed `scrape_all()` signature** to accept `selected_locations` parameter, resolving `TypeError` in Celery worker.
8. **Added `backend/tests/` suite** with 16 passing tests covering router path assertions, app imports, and core utilities.
9. **Fixed router path assertions** in tests to correctly check prefixed paths (`/jobs/`, `/user-profile/`).

## To-Do List
1. Implement automatic user profile creation upon resume upload (in `tasks_resume.py`).
2. Add API endpoint to accept and store user-selected preferred location.
3. Modify job scraping task to use user-selected location.
4. Create frontend flow for location selection after resume upload.
5. Extend job listing API to return full job description.
6. Integrate `ResumeTailor` to generate tailored resume for selected job.
7. Integrate `cover_letter_generator` to produce cover letter for selected job.
8. Ensure sequential triggering via Celery tasks/API callbacks with progress notifications.
9. Write unit/integration tests for new components.
10. Update documentation (`PROJECT_CONTEXT.md`, `FULL_PROJECT_STATE.md`) with new workflow.
