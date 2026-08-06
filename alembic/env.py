from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.database.base import Base

# Import all models so SQLAlchemy registers tables in Base.metadata
import app.database.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


settings = get_settings()


def get_sync_database_url() -> str:
    """
    Alembic uses a synchronous PostgreSQL driver.
    """

    url = settings.DATABASE_URL

    replacements = {
        "postgresql+asyncpg://": "postgresql+psycopg://",
        "postgresql://": "postgresql+psycopg://",
    }

    for old, new in replacements.items():
        if url.startswith(old):
            return url.replace(old, new, 1)

    return url


database_url = get_sync_database_url()

config.set_main_option(
    "sqlalchemy.url",
    database_url,
)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=False,
        )

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
