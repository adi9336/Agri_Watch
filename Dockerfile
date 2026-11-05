# ==============================================================================
# Multi-stage Dockerfile for Agri_watch Sovereign Indic Voice Engine & Web UI
# ==============================================================================

# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend Runtime
FROM python:3.12-slim AS runner
WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Copy compiled frontend from Stage 1 into /app/frontend/dist
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose HTTP port for FastAPI and Web SPA
EXPOSE 8000

ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Default command: launch unified FastAPI web server
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]

