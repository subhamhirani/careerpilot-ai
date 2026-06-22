# CareerPilot AI — Full Project State
Generated: 2026-06-20T16:40:04.920175+00:00

## Current Status
- Deployment: Fully operational, running on AWS via Docker Compose.
- Proxy: Caddy configured correctly, routing /api/* to backend (7899) and / to frontend (3000).
- Backend: FastAPI service (7899) stable, handling job listings, application flow, and settings.
- Frontend: Next.js (3000) stable, loading dashboard and settings correctly.
- Database: PostgreSQL (5432) + pgvector stable.

## Completed Tasks
- Caddyfile routing fixed (resolved 502 Bad Gateway and static asset issues).
- `NEXT_PUBLIC_API_URL` updated in `docker-compose.yml` to support `/api` routing.
- Dashboard scraper status card and API keys settings implemented.
- Job scraping pipeline (LinkedIn/Naukri) operational.
- Application workflow validated (status: applied/already_applied).

## Future TODOs / Roadmap
1. **Indeed Scraper:** Implement using proxy/Apify once keys are obtained.
2. **Resume Upload/Parsing:** Integrate `tasks_resume.py` with frontend upload endpoint.
3. **Approval UI:** Implement the pending approval review screen in the frontend.
4. **Scraper Trigger:** Implement the API endpoint `POST /scraper/trigger` and link it to the frontend button.
5. **Analytics/Visuals:** Enhance dashboard with full analytics visualization (funnel, trends).
6. **Notification System:** Implement email/Telegram alerts for application updates.

## Critical Configuration
- Backend DSN: Managed by `DATABASE_URL` environment variable.
- Caddy: Reverse proxy configuration in `/home/ubuntu/careerpilot/Caddyfile`.
- Environment: Python 3.11/14, Node 20.
