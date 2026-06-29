# ── Multi-stage build ─────────────────────────────────────────
# Builder stage: compile deps (includes gcc + Playwright install)
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build deps (will NOT carry to final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (including CPU torch for builder — needed for sentence-transformers download)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --upgrade --no-cache-dir \
        torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/* /tmp/*

# Run a quick import test / model download so it's cached
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder='/build/model_cache')" 2>/dev/null || true

# ── Runner stage: slim final image ────────────────────────────
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRANSFORMERS_CACHE=/app/model_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/model_cache

WORKDIR /app

# Install ONLY runtime system deps (no gcc, no UI libs, no Chromium)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy site-packages + torch from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy model cache
COPY --from=builder /build/model_cache /app/model_cache

# Copy application code
COPY . .

# Create non-root user and storage directory
RUN groupadd -r careerpilot && useradd -r -g careerpilot -d /app -s /bin/false careerpilot && \
    mkdir -p /app/storage/uploads && \
    chown -R careerpilot:careerpilot /app

USER careerpilot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:7899/health')"

EXPOSE 7899

# ── Entrypoint ───────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7899", "--workers", "1"]
