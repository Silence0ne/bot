#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h "$POSTGRES_HOST" -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
    sleep 2
done

echo "Applying migrations..."
alembic upgrade head

echo "Starting Quran Bot..."
exec python -m app
