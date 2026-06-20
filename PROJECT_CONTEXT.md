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
