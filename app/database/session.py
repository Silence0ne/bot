from __future__ import annotations

import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class Database:
    """
    Async database manager using SQLAlchemy.

    Handles:
    - Connection pooling
    - Session management
    - Connection lifecycle
    """

    def __init__(self) -> None:
        """Initialize database with connection pool."""
        from sqlalchemy.engine import make_url
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from app.core.config import get_settings

        settings = get_settings()
        database_url = settings.DATABASE_URL

        # Parse and validate URL
        try:
            url = make_url(database_url)
            logger.debug("Database URL parsed: driver=%s", url.drivername)
        except Exception as err:
            logger.warning(
                "Failed to parse DATABASE_URL: %s",
                err,
            )
            url = None

        # Convert PostgreSQL URL to asyncpg if needed
        if url and str(url.drivername).startswith("postgresql"):
            if url.drivername == "postgresql":
                database_url = database_url.replace(
                    "postgresql://",
                    "postgresql+asyncpg://",
                    1,
                )
                logger.debug("Converted URL to asyncpg driver")

            # If running locally for migration generation, use localhost if "postgres" host fails
            if url.host == "postgres":
                import os

                if not os.path.exists("/.dockerenv"):
                    database_url = database_url.replace("@postgres:", "@localhost:")
                    logger.info("Running outside Docker, using localhost for DB")

        # Create async engine with proper pooling
        self.engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
        )

        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("Database engine initialized")

    async def connect(self) -> None:
        """
        Test database connection.

        Raises:
            Exception: If connection fails
        """
        try:
            async with self.engine.begin() as conn:
                # Execute simple query to test connection
                await conn.exec_driver_sql("SELECT 1")

            logger.info("Database connected successfully")
        except Exception as exc:
            logger.exception("Failed to connect to database: %s", exc)
            raise

    @asynccontextmanager
    async def session(self):
        """
        Context manager for database sessions.

        Usage:
            async with database.session() as session:
                # Use session
                pass

        Yields:
            AsyncSession object
        """
        async_session = self.session_factory()
        try:
            yield async_session
        except Exception as exc:
            await async_session.rollback()
            logger.exception("Session error: %s", exc)
            raise
        finally:
            await async_session.close()

    async def dispose(self) -> None:
        """
        Dispose of all connections in pool.

        Should be called on shutdown.
        """
        try:
            await self.engine.dispose()
            logger.info("Database connection pool disposed")
        except Exception as exc:
            logger.exception("Failed to dispose database: %s", exc)

    async def close(self) -> None:
        """
        Close database engine.

        Should be called during application shutdown.
        """
        await self.dispose()
        logger.info("Database closed")
