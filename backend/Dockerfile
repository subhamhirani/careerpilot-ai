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
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (CPU-only torch to avoid CUDA GPU packages)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt && \
    rm -rf /root/.cache/* /tmp/*

# Install Playwright chromium browser (without --with-deps to avoid unavailable font packages)
RUN playwright install chromium 2>&1 || true
# Install only the font packages that are available
RUN apt-get install -y --no-install-recommends \
    fonts-liberation \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    2>&1 || true

# Remove build deps
RUN apt-get purge -y gcc && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Create non-root user and upload directory
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
