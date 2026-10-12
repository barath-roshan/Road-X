# ==============================================================================
# RoadX Production & Container Deployment Dockerfile (Phase 22)
#
# Builds a secure, minimal container running the RoadX FastAPI ML Service.
# Employs a non-root system user, layer caching, and healthcheck probes.
# ==============================================================================

FROM python:3.11-slim

# Build-time labels
LABEL maintainer="RoadX Engineering Team"
LABEL description="RoadX Intelligent Road Grievance & Maintenance Management Service"
LABEL version="1.0.0"

# Python runtime configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ROADX_PROJECT_ROOT=/app \
    ROADX_ENV=production

# Install minimal OS dependencies for OpenCV, network healthchecks, and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group
RUN groupadd -g 1001 roadx && \
    useradd -u 1001 -r -g roadx -d /app -s /sbin/nologin roadx

# Set working directory
WORKDIR /app

# Copy dependency specifications first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies reproducibly
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create necessary runtime directories before copying code
RUN mkdir -p /app/data /app/models /app/logs /app/models/monitoring /app/data/uploads && \
    chown -R roadx:roadx /app

# Copy application packages and configuration
COPY --chown=roadx:roadx api /app/api
COPY --chown=roadx:roadx backend /app/backend
COPY --chown=roadx:roadx ml /app/ml
COPY --chown=roadx:roadx models /app/models
COPY --chown=roadx:roadx data/knowledge /app/data/knowledge
COPY --chown=roadx:roadx alembic /app/alembic
COPY --chown=roadx:roadx alembic.ini /app/alembic.ini
COPY --chown=roadx:roadx docker-entrypoint.sh /app/docker-entrypoint.sh

# Grant execution permissions on the entrypoint script
RUN chmod +x /app/docker-entrypoint.sh

# Expose FastAPI application port
EXPOSE 8000

# Container healthcheck probe (polls /health endpoint every 30s)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run as non-privileged user
USER roadx

# Container execution configuration
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
