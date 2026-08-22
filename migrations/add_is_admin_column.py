"""
Migration script to add is_admin column to chats table.

Run this script to update your database schema:
python -m app.migrations.add_is_admin_column
"""

import asyncio
import logging
from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_is_admin_column():
    """Add is_admin column to chats table if it doesn't exist."""
    get_settings()
    database = Database()

    try:
        await database.connect()

        async with database.session() as session:
            # Check if column exists
            check_column_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'chats'
                AND column_name = 'is_admin'
            """)

            result = await session.execute(check_column_query)
            column_exists = result.fetchone()

            if column_exists:
                logger.info("Column 'is_admin' already exists in chats table")
                return

            # Add the column
            alter_query = text("""
                ALTER TABLE chats
                ADD COLUMN is_admin BOOLEAN DEFAULT FALSE
            """)

            await session.execute(alter_query)
            await session.commit()

            logger.info("Successfully added 'is_admin' column to chats table")

    except Exception as e:
        logger.error(f"Failed to add is_admin column: {e}")
        raise
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(add_is_admin_column())
