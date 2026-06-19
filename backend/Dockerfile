# ── Single-stage build ─────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system runtime deps + build deps, then remove build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (CPU-only torch to avoid CUDA GPU packages)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt && \
    rm -rf /root/.cache/* /tmp/*

# Remove build dep
RUN apt-get purge -y gcc && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r careerpilot && useradd -r -g careerpilot -d /app -s /bin/false careerpilot && \
    chown -R careerpilot:careerpilot /app
USER careerpilot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:7899/health')"

EXPOSE 7899

# ── Entrypoint ───────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7899", "--workers", "1"]
