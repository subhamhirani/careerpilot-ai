# DEPLOYMENT LOG - CareerPilot Production Deployment

## Deployment Summary

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-07-03 |
| **Public IP** | http://3.109.213.250 |
| **Status** | ✅ **FULLY DEPLOYED & OPERATIONAL** |
| **Stack** | Docker Compose (9/9 services healthy) |
| **Reverse Proxy** | Caddy (ports 80/443) |
| **Backend** | FastAPI on port 7899 (internal, via Caddy) |
| **Frontend** | Next.js 14 on port 3000 (internal, via Caddy) |
| **SSL** | Caddy auto-SSL (needs domain for HTTPS) |

---

## Services (All Healthy)

```
NAME                         STATUS        PORTS                    NOTES
careerpilot-backend          Up 30h        0.0.0.0:7899->7899      FastAPI — internal only
careerpilot-frontend         Up 30h        0.0.0.0:3000->3000        Next.js 14 — internal only
careerpilot-caddy            Up 30h        0.0.0.0:80->80, :.Endpoint443          Reverse proxy + auto-SSL
careerpilot-postgres         Up 30h        127.0.0.1:5432->5432      PostgreSQL + pgvector
careerpilot-redis            Up 30h        127.0.0.1:6379->6379      Redis cache
careerpilot-worker           Up 30h        7899/tcp                  Celery worker
careerpilot-beat             Up 30h        7899/tcp                  Celery beat scheduler
careerpilot-monitor          Up 30h        0.0.0.0:3001->3001        Uptime-Kuma monitoring
careerpilot-resume-agent-1   Up 30h        8002/tcp                  Resume matcher microservice
```

---

## Build Process (Working)

The "BuildKit + Bake" warning is harmless. Build falls back to legacy builder and succeeds.

### Backend Build
```bash
cd /home/ubuntu/careerpilot/backend
docker build -f Dockerfile -t careerpilot-backend .
```
- **Base image**: `python:3.11-slim`
- **Cache**: SentenceTransformer model cached in `/app/model_cache`
- **Result**: ✅ Builds successfully

### Worker / Beat Build
```bash
# Same image as backend, different CMD
docker compose build worker
docker compose -f docker-compose.yml up -d --force-recreate worker
```

### Frontend Build
```bash
cd /home/ubuntu/careerpilot/frontend
npm ci --legacy-peer-deps    # phosphor-icons installs correctly
npm run build                  # Next.js standalone output
```
- **Base image**: `node:20-alpine`
- **Output mode**: `standalone` (produces `server.js`)
- **Result**: ✅ Builds successfully
- **Note**: `@phosphor-icons/react` is already in `package.json` and installs fine.

---

## Known Issues & Fixes

### 1. ✅ FIXED — Schema Bug in `tasks_scraper.py`
- **Problem**: `SELECT jp.company` — column doesn't exist
- **Fix**: Use `LEFT JOIN companies c ON jp.company_id = c.id` + `c.name as company`
- **Commit**: `8330588`

### 2. ⚠️ Next.js Server Actions Warning
- **Message**: `x-forwarded-host header with value 3.109.213.250:80 does not match origin header`
- **Impact**: Server Actions may fail when accessed via raw IP + port
- **Fix**: Add a domain name (see DNS section below)
- **Workaround**: Use API routes instead of Server Actions for forms

---

## Quick Deployment Commands

```bash
# Full stack rebuild & restart
cd /home/ubuntu/careerpilot
docker compose -f docker-compose.yml up -d --build

# Rebuild single service
docker compose -f docker-compose.yml build backend
docker compose -f docker-compose.yml up -d --force-recreate backend

# View logs
docker logs careerpilot-backend --tail 50
docker logs careerpilot-worker --tail 50
docker logs careerpilot-frontend --tail 50

# DB shell
docker exec -it careerpilot-postgres psql -U careerpilot

# Worker health check
docker exec careerpilot-worker celery -A app.celery_config.celery_app inspect ping
```

---

## DNS Configuration (Pending)

To enable HTTPS and fix Next.js Server Actions, add a domain:

1. **Register/point a domain** to `3.109.213.250` (A record)
2. **Update Caddyfile** (if using custom Caddy config) or let Caddy auto-handle
3. **Update Next.js env**:
   ```
   NEXT_PUBLIC_APP_URL=https://yourdomain.com
   ```
4. **Rebuild frontend** with new env

Current recommendation: Use AWS Route 53 or any DNS provider with an A record pointing to `3.109.213.250`.

---

## Environment Variables

Key `.env` values ( production ):

```bash
DATABASE_URL=postgresql+asyncpg://careerpilot:careerpilot_secret@postgres:5432/careerpilot
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

---

## Verification Checklist

- [x] All 9 Docker containers running and healthy
- [x] Backend API responds on /health
- [x] Frontend serves on port 3000
- [x] Caddy proxies port 80 → frontend
- [x] PostgreSQL + pgvector operational
- [x] Redis operational
- [x] Celery worker processing tasks
- [x] Resume upload pipeline working (tested with real PDF)
- [x] Job matching pipeline fixed and deployed
- [ ] DNS domain configured (pending)
- [ ] HTTPS enabled via Caddy (pending domain)

---

*Log updated: 2026-07-03*
