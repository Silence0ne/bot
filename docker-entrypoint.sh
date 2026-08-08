#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."

until pg_isready -h postgres -U postgres -d quran_bot; do
    sleep 2
done

echo "Generating migrations from models (if any)..."
MIGRATION_OUTPUT=$(alembic revision --autogenerate -m "auto")
echo "$MIGRATION_OUTPUT"

# Extract the generated file path from alembic's output (e.g., "Generating /app/.../xxx_auto.py")
MIGRATION_FILE=$(echo "$MIGRATION_OUTPUT" | grep -oE '/[^ ]+\.py' | head -n 1)

# If a file was generated, check if it contains actual DB operations (op.xxx)
if [ -n "$MIGRATION_FILE" ] && [ -f "$MIGRATION_FILE" ]; then
    if ! grep -q "op\." "$MIGRATION_FILE"; then
        echo "No schema changes detected. Removing empty migration file."
        rm "$MIGRATION_FILE"
    else
        echo "New migration created: $MIGRATION_FILE"
    fi
fi

echo "Applying migrations..."
alembic upgrade head

echo "Starting Quran Bot..."
exec python -m app
