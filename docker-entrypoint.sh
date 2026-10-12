#!/bin/sh
set -e

# ==============================================================================
# RoadX Container Entrypoint Script
# Handles optional startup database migrations and passes execution to command
# ==============================================================================

echo "[entrypoint] Starting RoadX container initialization..."

# Run database migrations if explicitly enabled or if in auto-migration mode
if [ "${RUN_MIGRATIONS}" = "true" ] || [ "${AUTO_MIGRATE}" = "true" ]; then
    echo "[entrypoint] RUN_MIGRATIONS is set to true. Applying Alembic migrations..."
    if alembic upgrade head; then
        echo "[entrypoint] Alembic migrations applied successfully to head."
    else
        echo "[entrypoint] ERROR: Alembic database migration failed!" >&2
        exit 1
    fi
else
    echo "[entrypoint] Skipping automatic migrations (RUN_MIGRATIONS is not 'true')."
fi

# Ensure required runtime directories exist and are writable
mkdir -p /app/data /app/models/monitoring /app/logs /app/data/uploads

echo "[entrypoint] Initialization complete. Executing command: $@"
exec "$@"
