#!/bin/sh
set -eu

echo "Running migrations..."
alembic -c alembic/alembic.ini upgrade head

echo "Starting bot..."
exec python -m app

