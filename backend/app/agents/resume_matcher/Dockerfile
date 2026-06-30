# Minimal Dockerfile for the lightweight résumé‑matcher micro‑service
FROM python:3.14-slim

WORKDIR /app

COPY . /app

# Install only the required fastapi stack (no heavy ML packages)
RUN pip install fastapi uvicorn python-multipart

EXPOSE 8002

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
