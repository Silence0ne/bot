"""
Migration script to add daily_type column to chats table.

This migration adds a new field to track the daily content type preference (ayah/page).
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text  # noqa: E402
from app.database.session import Database  # noqa: E402


async def migrate():
    """Add daily_type column to chats table."""
    db = Database()

    try:
        async with db.session() as session:
            # Check if column already exists
            result = await session.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'chats' AND column_name = 'daily_type'
                """))
            exists = result.fetchone()

            if exists:
                print(
                    "Column 'daily_type' already exists in chats table. Skipping migration."
                )
                return

            # Add the column
            await session.execute(text("""
                    ALTER TABLE chats
                    ADD COLUMN daily_type VARCHAR(10) DEFAULT 'ayah'
                """))

            await session.commit()
            print("Successfully added 'daily_type' column to chats table.")

    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(migrate())
