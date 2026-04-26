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

# Create a non-root user
RUN adduser --disabled-password --gecos "" appuser

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose port (Railway/Render will override this, but it's good practice)
EXPOSE 8000

# Start with Gunicorn for high-performance parallel processing
# -w 4: Run 4 worker processes (adjust based on your Railway plan)
# -k uvicorn.workers.UvicornWorker: Use the ultra-fast Uvicorn worker
CMD ["sh", "-c", "python app/prestart.py && gunicorn -w ${WEB_WORKERS:-4} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120 --access-logfile - app.main:app"]

