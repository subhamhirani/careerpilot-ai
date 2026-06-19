# Changelog

## v1.0.0 (2026-06-16)

### Initial Release

- **Agent 1 - Resume Analysis:** PDF/DOCX parsing, Groq structured extraction, embedding generation
- **Agent 2 - Job Discovery:** Scrapers for LinkedIn, Naukri, Indeed India with rate limiting and deduplication
- **Agent 3 - Job Matching:** Two-phase scoring (local embeddings + Groq LLM), 7-dimension match analysis
- **Agent 4 - Resume Tailoring:** JD-aware resume optimization with safety checks
- **Agent 5 - Cover Letter:** Tone-customizable cover letter generation
- **Agent 6 - Application:** Playwright automation with manual fallback
- **Telegram Bot:** Full command set (/status, /jobs, /approve, /reject, /stats)
- **FastAPI Backend:** RESTful API, JWT auth with TOTP 2FA, Celery tasks
- **Next.js Frontend:** Dashboard, job feed, approvals, analytics, resume management
- **Database:** PostgreSQL 15 with pgvector, 14 tables, alembic migrations
- **Infrastructure:** Docker Compose, Caddy reverse proxy, health checks
