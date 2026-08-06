#!/bin/sh
set -eu

echo "Waiting for PostgreSQL..."

until pg_isready -h postgres -U postgres -d quran_bot; do
    sleep 2
done

echo "Running migrations..."
alembic upgrade head

echo "Starting Quran Bot..."
exec python -m app
