# Multi-stage build для Render
# Этот Dockerfile находится в КОРНЕ репозитория

FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends     gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

# Python deps (из backend/)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (из backend/)
COPY backend/ .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
