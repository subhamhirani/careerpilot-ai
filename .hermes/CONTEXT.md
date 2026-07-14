# CareerPilot — Project Context (for AI agents)

## Project Overview
CareerPilot is a multi-agent job matching and career development platform. FastAPI backend + Next.js 14 frontend, PostgreSQL (pgvector), Celery + Redis, Docker Compose deployment.

## Active Deployment
- **Public IP**: http://3.109.213.250 (Caddy proxy, port 80 → backend :7899, frontend :3000)
- **Domain**: none configured yet (raw IP only)
- **Security Groups**: AWS — ports 22, 80, 3000 open (7899 blocked intentionally, Caddy handles it)
- **GitHub**: https://github.com/subhamhirani/careerpilot-ai (branch: main)

## All 9 Containers Running (healthy)
```
careerpilot-backend   (FastAPI, port 7899)     Up 29h
careerpilot-frontend  (Next.js, port 3000)     Up 29h
careerpilot-caddy     (reverse proxy)          Up 29h
careerpilot-postgres  (PostgreSQL + pgvector)  Up 29h
careerpilot-redis     (Redis cache)            Up 29h
careerpilot-worker    (Celery worker)          Up 26m
careerpilot-beat      (Celery beat scheduler)  Up 29h
careerpilot-monitor   (Uptime-Kuma, port 3001) Up 29h
careerpilot-resume-agent-1                     Up 29h
```

## Project Structure
```
backend/app/
├── agents/          — Multi-agent orchestration (resume analysis, matching, scraping)
├── providers/       — FIXED! Provider abstraction layer (NEW — 15 files, 934 LOC)
│   ├── base.py      — ABCs: ScraperProvider, ResumeProvider, MatcherProvider
│   ├── factory.py   — @register decorator + auto-discovery
│   ├── dependencies.py — FastAPI Depends() helpers
│   ├── scraper/     — native.py (wraps existing) + api.py (stub)
│   ├── resume/      — native.py (wraps existing) + api.py
│   └── matcher/     — native.py (wraps existing) + api.py
├── routers/         — FastAPI route handlers (16 routers)
│   ├── auth.py, jobs.py, matches.py, resumes.py, scraper.py, ...
│   ├── resume_parsing.py, resume_matcher.py, applications.py, ...
│   └── cover_letters.py, approvals.py, onboarding.py, dashboard.py, ...
└── auth.py, main.py, tasks.py, tasks_scraper.py, tasks_resume.py, ...
```

## Pipeline Test Results (verified 2026-07-14)
| Step | Status | Details |
|------|--------|---------|
| Login (subham@example.com) | ✅ | Token obtained |
| Jobs in DB | ✅ | 3009 job_postings (LinkedIn/Naukri/Indeed sources) |
| Resume Upload (PDF + TXT) | ✅ | Works via multipart POST |
| Resume Parsing | ✅ | **Subham: 69 skills extracted** (was broken — see Fixed Issues) |
| Trigger Scrape | ✅ | 120 LinkedIn jobs scraped for India (Indeed blocked 403, Naukri 0) |
| Trigger Re-rank | ✅ | 200 OK |
| Score Jobs (`/api/scraper/score-jobs`) | ✅ | 200 jobs scored for Subham |
| Matches Produced (Subham) | ✅ | **200 matches** with scores/tiers/companies |

## FIXED ISSUES (2026-07-14)
### 1. Decommissioned LLM models (was BLOCKING all resume parsing)
`llm_client.py` defaulted to `groq: llama3-70b-8192` (400 decommissioned) and
`gemini: gemini-1.5-flash` (404 not found). `query_llm()` fell through to
`AllProvidersExhausted`, so `_parse_resume_with_llm()` silently returned `{}`,
leaving `user_profiles` with no skills → 0 matches for everyone.
**Fix**: `llama-3.3-70b-versatile` (groq) + `gemini-2.0-flash` (gemini). Committed `5f18d57`.

### 2. Plain-text resume extraction missing
`_extract_text_from_file()` returned `''` for any non-PDF/DOCX. Text resumes
(now the common case) failed to parse.
**Fix**: handle TXT/MD uploads. Committed `5f18d57`.

### 3. Schema bug `tasks_scraper.py:426` (was BLOCKING matching)
Fixed 2026-07-03 (`8330588`): `jp.company` → `c.name` + `LEFT JOIN companies`.
Deployed; 10,800 match_scores exist (mostly seeded test users).

### 4. Subham's profile had no parsed data
His stored PDF was image-based (no extractable text). Uploaded his real
`subham_hirani_resume.txt`, parsed it (69 skills), set `preferred_location='India'`.
Re-scored → 200 matches.

## KNOWN ISSUES — Remaining
### 1. DNS domain NOT configured (BLOCKING HTTPS + Next.js Server Actions)
Live site is raw IP `http://3.109.213.250`. Needs: register a domain → A record
→ `3.109.213.250` → update Caddyfile → rebuild frontend. **Requires user to buy a
domain (~$10-15/yr).** Guide: `docs/status/DNS_SETUP.md`. NOT auto-fixable.
- Impact: Caddy can't get Let's Encrypt cert; Next.js Server Actions warn on raw IP.
- Workaround: API routes work fine (matching/parsing all functional via API).

### 2. Indeed scraper returns 403
`in.indeed.com` blocks automated requests (403 Forbidden). LinkedIn + Naukri work.
Consider BrightData/Scrapling proxy for Indeed (Scrapling integration added 2026-07-13).

### 2b. Standalone resume-matched scraping → Telegram (`scrapling_integration.py`)
Independent of the DB/Celery pipeline; scrapes LinkedIn guest search directly and
delivers a ranked top-50 report to the live Telegram gateway. Rewritten 2026-07-14.
- **Engine = LinkedIn only.** Naukri's public API (and the Scrapling Fetcher hitting
  it) returns the SAME ~20 unrelated jobs regardless of query from this datacenter IP.
  Keyless APIs (remotive/themuse/arbeitnow) ignore queries entirely (cashiers/writers).
  Both excluded as noise.
- **27 resume-targeted role queries** @ "Ahmedabad, Gujarat" → ~220 unique jobs,
  ~60 resume-relevant after a strict relevance gate.
- **Relevance gate**: positive title regex (network/infra/sysadmin/security/cloud/
  devops/support) OR skill overlap ≥3; negative regex drops sales/finance/law/VLSI/
  electrical/medical/HR/software-dev. `NoC` is NOT matched (it's VLSI Network-on-Chip,
  not Network Operations Center).
- **Scoring**: best title-relevance weight + min(30, skill_overlap*2) + location tier
  (Gujarat +10 > Remote +6 > India +4 > Intl +2). Location is a TIEBREAKER, not a
  dominator (old bug: +15 Gujarat boost pushed unrelated pan-India jobs to top).
- **Run**: `/home/ubuntu/scrapling-venv/bin/python scrapling_integration.py`
  (`--dry-run` validates ranking w/o Telegram; `--use-cache` reuses `artifacts/
  cache_scrapling.json`). Reads `TELEGRAM_BOT_TOKEN` / `TELEGRAM_ALLOWED_USER_ID` from `.env`.
- **LinkedIn 429 fix** (multi_portal_scraper.py): 4× retry w/ 5s·attempt backoff.
- **Artifacts**: `job_report_YYYY-MM-DD_scrapling.md` (ranked report),
  `top50_scrapling.json` (machine-readable), `cache_scrapling.json` (raw scrape).

### 3. LinkedIn-scraped jobs require generic SWE skills
Subham's infra/network profile shows `missing=66-69` on SWE roles (expected — his
skills are network/infra). Match relevance is accurate; the jobs are just poor fits.

## Provider Ecosystem (NEW — committed in 4ae658d)
- **Abstract base classes** for Scraper, Resume, Matcher providers
- **Native implementations** wrap existing agent code
- **API implementations** expose REST-based alternatives
- **Factory pattern** with `@register` decorator, auto-discovers providers
- **Dependency injection** via FastAPI `Depends(get_scraper_provider etc.)`
- Auto-registered in `app.main` on startup

## API Endpoints Quick Reference
```
POST  /api/auth/login              → token
POST  /api/auth/register           → user
POST  /api/resumes/upload          → multipart file upload
GET   /api/resumes                 → list resumes
GET   /api/jobs                    → list jobs (20 default)
POST  /api/scraper/trigger         → start scraping (requires location)
POST  /api/matches/re-rank         → trigger matching
GET   /api/matches/                → list match scores
GET   /api/matches/{id}            → match detail
```

## Test Credentials
| Field | Value |
|-------|-------|
| Email | subham@example.com |
| Password | test123456 |
| User ID UUID | d3324f0f-093e-47c6-8ff6-72c6b6cf4930 |

## Git History (recent)
```
4ae658d  feat: add provider abstraction layer (15 files, 934 LOC)
4c88c95  feat: complete Vercel deployment pipeline + optimize icons
ca23078  Sync: automated sync 2026-07-02_07-05-59
db8eb58  feat(scraper): add selected_locations parameter
d523842  fix: remove nested html/body in auth layout
1420105  fix: correct match_grade enum value from 'poor' to 'POOR'
```

## Next Actions (priority order)
1. ✅ Fix `tasks_scraper.py:426` — done 2026-07-03 (`8330588`)
2. ✅ Set user preferred_location — done (India)
3. ✅ Re-test full pipeline (scrape→upload→match→verify) — done 2026-07-14 (200 matches)
4. ⏸ **Add domain name** (DNS → Caddy) — BLOCKED on user buying a domain (~$10-15/yr). Guide: `docs/status/DNS_SETUP.md`
5. ✅ BuildKit warning — documented as harmless in DEPLOYMENT_LOG.md (legacy fallback succeeds)

## Useful Commands
```bash
cd /home/ubuntu/careerpilot
docker compose -f docker-compose.yml up -d              # Full stack
docker logs careerpilot-worker --tail 50                 # Worker logs (real-time)
docker logs careerpilot-backend --tail 50                # API logs
docker exec -it careerpilot-postgres psql -U careerpilot # DB shell
python3 -c "..."                                         # Test API (use urllib, not curl)
```

## Environment
- Python 3.11 in Docker containers
- Node 18+ for frontend
- DB URL: `postgresql+asyncpg://careerpilot:careerpilot@postgres:5432/careerpilot`
- Redis: `redis://redis:6379/0`
- Caddy: auto-SSL ready (needs domain)
