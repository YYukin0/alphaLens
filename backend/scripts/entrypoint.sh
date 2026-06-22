#!/bin/bash
set -e

PORT="${PORT:-8000}"
APP_MODE="${1:-api}"

if [[ "${DATABASE_URL}" == postgres://* ]]; then
  export DATABASE_URL="${DATABASE_URL/postgres:\/\//postgresql:\/\/}"
fi

echo "Waiting for PostgreSQL..."
for attempt in $(seq 1 90); do
  if python -c "import psycopg2; psycopg2.connect('${DATABASE_URL}')" 2>/dev/null; then
    break
  fi
  if [ "$attempt" -eq 90 ]; then
    echo "PostgreSQL not ready after 90 seconds."
    exit 1
  fi
  sleep 1
done
echo "PostgreSQL is ready."

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
else
  echo "Skipping database migrations (SKIP_MIGRATIONS=true)."
fi

case "$APP_MODE" in
  api)
    if [ -n "${RAILWAY_ENVIRONMENT_NAME:-}" ] || [ "${APP_ENV:-}" = "production" ]; then
      exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
    else
      exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
    fi
    ;;
  worker)
    exec celery -A app.celery_app worker \
      --loglevel="${CELERY_LOG_LEVEL:-info}" \
      -Q filings,prices,events,celery \
      --concurrency="${CELERY_CONCURRENCY:-2}"
    ;;
  *)
    exec "$@"
    ;;
esac
