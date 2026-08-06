#!/bin/sh

set -eu

echo "Waiting for PostgreSQL..."

until alembic current >/dev/null 2>&1; do
    sleep 2
done

echo "Running migrations..."

alembic upgrade head

echo "Starting Quran Bot..."

exec python -m app
