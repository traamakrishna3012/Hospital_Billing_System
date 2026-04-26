# Unified Multi-Stage Dockerfile for Hospital Billing System
# --- Stage 1: Build Frontend ---
# Force Rebuild ID: BUILD_2026_04_26_V2
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Backend & Final Image ---
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user and set up working directory
RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p /app/static /app/uploads && \
    chown -R appuser:appuser /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage cache
COPY --chown=appuser:appuser backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source with correct ownership
COPY --chown=appuser:appuser backend/ ./

# Copy built frontend from Stage 1
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist ./static

# Switch to the non-root user
USER appuser

# Expose port
EXPOSE 8000

# Start with Gunicorn
CMD ["sh", "-c", "python app/prestart.py && gunicorn -w ${WEB_WORKERS:-2} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120 --access-logfile - app.main:app"]

