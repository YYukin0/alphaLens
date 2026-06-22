#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until python -c "import psycopg2; psycopg2.connect('${DATABASE_URL}')" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL is ready."

echo "Running database migrations..."
alembic upgrade head

case "$1" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ;;
  worker)
    exec celery -A app.celery_app worker --loglevel=info -Q filings,prices,events,celery
    ;;
  *)
    exec "$@"
    ;;
esac
