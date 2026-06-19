# CareerPilot AI

Personalized Multi-Agent Job Search & Application Platform

**Owner:** Subham | **Location:** Ahmedabad, India  
**Target Roles:** DevOps / Cloud / Infrastructure / SRE / Platform / IT Support  
**Running Cost:** ₹0/month (beyond existing VPS)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Tech Stack (100% Free)](#tech-stack-100-free)
- [Prerequisites](#prerequisites)
- [Installation & Development Setup](#installation--development-setup)
- [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [CI/CD Pipeline](#cicd-pipeline)
- [Monitoring](#monitoring)
- [Backups](#backups)
- [Contributing Guidelines](#contributing-guidelines)
- [License](#license)
- [Directory Structure](#directory-structure)

---

## Project Overview

CareerPilot AI is an automated job‑search and application platform that leverages multiple AI agents to streamline the job hunt process:

- **Resume Analysis Agent** – extracts skills, experience, and preferences from uploaded resumes.  
- **Job Discovery Agent** – scrapes job boards (LinkedIn, Naukri, Indeed, etc.) using LLMs.  
- **Job Matching Agent** – matches user profiles with relevant postings.  
- **Cover Letter & Resume Tailoring Agents** – generate personalized application documents.  
- **Application Agent** – automatically submits applications via Playwright.  
- **Telegram Bot** – provides status updates, manual approvals, and notifications.

All components run on a **free** technology stack, making it possible to host the entire system on an existing VPS at zero additional cost.

---

## Features

- **Intelligent Resume Parsing** – natural‑language extraction of competencies and experience levels.  
- **Dynamic Job Scraping** – supports multiple job boards; fallback LLM integration for parsing unstructured listings.  
- **Real‑time Matching Engine** – uses embeddings (sentence‑transformers) to rank suitability.  
- **Automated Application Workflow** – from application draft to final submission, fully headless via Playwright.  
- **Telegram Integration** – instant alerts, status checks, and manual approval steps.  
- **Batch Processing** – nightly job discovery (08:00) → digest generation (09:00) → automated matching.  
- **Extensible Agent Framework** – add new agents or modify existing logic without touching core services.

---

## Tech Stack (100% Free)

| Component      | Technology                                    | Cost |
|----------------|-----------------------------------------------|------|
| LLM            | Groq (Llama 3.3 70B) + Gemini Flash fallback  | Free |
| Embeddings     | `sentence-transformers/all‑MiniLM‑L6‑v2`      | Free |
| Database       | PostgreSQL 15 + `pgvector` extension          | Free |
| Cache / Queue  | Redis 7 + Celery                              | Free |
| Backend        | FastAPI (Python 3.11+)                        | Free |
| Frontend       | Next.js 14 + Tailwind CSS + shadcn/ui         | Free |
| Browser Automation | Playwright (headless Chromium)          | Free |
| Proxy / HTTPS  | Caddy (auto‑HTTPS via Let’s Encrypt)          | Free |
| Notifications  | Telegram Bot API                              | Free |
| Hosting        | Existing VPS                                  | ₹0 extra |

**Total monthly cost:** **₹0** beyond your current VPS.

---

## Prerequisites

- **Docker** (≥ 20.10) and **Docker Compose** (≥ 2.0) installed.
- **Python** 3.11+ (for local development).
- **Node** 20+ (for frontend tooling).
- Access to the following free services:
  - [Groq](https://console.groq.com) – LLM API key.
  - [Google AI Studio](https://aistudio.google.com) – fallback LLM API key.
  - [Telegram BotFather](https://t.me/BotFather) – bot token.
- A domain name pointed to your server (for HTTPS via Caddy).

---

## Installation & Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/subhamhirani/careerpilot-ai.git
cd careerpilot
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your API keys and other settings
```

### 3. Install backend dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
npm run build   # optional, for static generation
```

### 5. Run database migrations

```bash
docker compose up -d
docker compose exec backend alembic upgrade head
```

### 6. Start development servers

```bash
# Backend
cd ../backend
uvicorn app.main:app --reload --port 8000

# Frontend
cd ../frontend
npm run dev
```

### 7. Health check

```bash
curl http://localhost:8000/health
```

---

## Docker Deployment

A full production stack is defined in `docker-compose.yml`. The workflow is:

```bash
# Build and start containers
docker compose up -d

# Apply migrations (run once or as part of CI)
docker compose exec backend alembic upgrade head

# Verify health
curl https://careerpilot.yourdomain.com/health
```

The stack includes:

- `backend` – FastAPI application
- `frontend` – Next.js client
- `postgres` – PostgreSQL with pgvector
- `redis` – Cache & Celery queue
- `caddy` – Reverse proxy with automatic HTTPS
- `celery worker` & `celery beat` – scheduled jobs

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq LLM API key | `gsk_...` |
| `GOOGLE_AI_STUDIO_KEY` | Gemini fallback key | `AIza...` |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | `123456:ABC...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@db:5432/careerpilot` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `JWT_SECRET` | Secret for JWT signing | `supersecret` |
| `ENV` | Environment identifier (`dev`, `prod`) | `prod` |

Copy `.env.example` to `.env` and fill in the values. Sensitive data should **never** be hard‑coded.

---

## API Documentation

- **OpenAPI/Swagger**: `https://careerpilot.yourdomain.com/docs`
- **ReDoc**: `https://careerpilot.yourdomain.com/redoc`
- **Telegram Bot API**: `https://api.telegram.org/bot<token>/METHOD_NAME`

All endpoints are versioned under `/api/v1/`. Authentication is performed via JWT (`Authorization: Bearer <token>`).

---

## CI/CD Pipeline

The repository uses **GitHub Actions** for automated testing, building, and deployment.

```mermaid
graph LR
    A[Push to main] --> B[CI: Lint & Test]
    B --> C[Build Docker Images]
    C --> D[Run Unit & Integration Tests]
    D --> E[Push Images to Docker Hub]
    E --> F[Deploy to VPS (SSH)]
    F --> G[Restart Services]
    G --> H[Run Database Migrations]
```

- **Linting**: `ruff` (Python) and `eslint` (JS).
- **Testing**: `pytest` for backend, `jest` for frontend.
- **Docker Build**: Multi‑stage builds to keep images slim.
- **Deploy**: SSH into your VPS, pull latest images, run `docker compose up -d`, and execute migrations.

Configuration resides in `.github/workflows/ci.yml`.

---

## Monitoring

- **Uptime Kuma** monitors all public endpoints (`/health`, `/status`, etc.) and sends alerts to Telegram.
- **Celery Beat** logs job execution; failures trigger notifications.
- **Caddy** access logs are rotated and stored in `/var/log/caddy`.
- **Prometheus** metrics can be scraped if enabled (optional).

Dashboard URLs:

- Uptime Kuma: `https://uptime.careerpilot.yourdomain.com`
- Prometheus (optional): `https://prometheus.careerpilot.yourdomain.com`

---

## Backups

- **PostgreSQL**: Daily logical dumps via `pg_dumpall` scheduled in Docker Compose.
- **Redis**: RDB snapshots are persisted to a host volume; copy periodically.
- **File Storage**: Static uploads (if any) are stored on the host; versioned backups are kept in `/backups`.

Backup scripts are located in `scripts/backup.sh` and can be triggered manually or via a cron job.

---

## Contributing Guidelines

1. **Fork** the repository and create a feature branch (`feat/your‑feature`).
2. **Run tests** locally (`pytest` / `npm test`) and ensure 100% coverage for new code.
3. **Follow the coding style**:
   - Python: PEP 8 + `ruff` formatting.
   - JavaScript/TypeScript: `eslint` + `prettier`.
4. **Commit** with clear, imperative messages (`docs: add README`, `feat: add job‑matching agent`).
5. **Open a Pull Request** – the CI pipeline will run automatically.
6. **Address review comments** promptly; squash‑merge only when all checks pass.

Please read the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for detailed policies.

---

## License

This project is released under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## Directory Structure

```
/careerpilot
├── backend/
│   ├── app/
│   │   ├── agents/          # AI agents (resume, job, matching, etc.)
│   │   ├── main.py           # FastAPI entry point
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── auth.py           # JWT + 2FA logic
│   │   ├── bot.py            # Telegram bot
│   │   ├── llm_client.py     # Groq/Gemini abstraction
│   │   └── agencies.py       # DB session & utilities
│   ├── alembic/               # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js pages
│   │   ├── components/        # UI components
│   │   ├── lib/               # API client + stores
│   │   └── types/             # TypeScript types
│   ├── Dockerfile
│   └── next.config.js
├── docker-compose.yml
├── Caddyfile
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
└── README.md
```

---

### 🎉 You're all set!

Start exploring, contributing, or deploying your own instance of CareerPilot AI. Happy job hunting! 🚀