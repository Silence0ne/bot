from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import create_engine

# Import every model so SQLAlchemy registers all tables.
# Keep this import. Without it Alembic sees an empty metadata.
import app.database.models  # noqa: F401
from alembic import context
from app.core.config import get_settings
from app.database.base import Base
from app.database.types import UUIDType

config = context.config
settings = get_settings()


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_sync_database_url() -> str:
    """
    Alembic migrations run synchronously.
    Convert async application URLs into sync PostgreSQL URLs.
    """

    url = settings.DATABASE_URL
    if "asyncpg" in url:
        url = url.replace("+asyncpg", "")

    return url


config.set_main_option("sqlalchemy.url", get_sync_database_url())

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """
    Teach Alembic how to render custom SQLAlchemy types.
    """

    if type_ == "type":
        if isinstance(obj, UUIDType):
            autogen_context.imports.add("from app.database.types import UUIDType")
            return "UUIDType()"

    return False


def run_migrations_offline() -> None:
    """
    Run migrations without creating a database connection.
    """

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
        render_item=render_item,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations using a live database connection.
    """

    engine = create_engine(
        config.get_main_option("sqlalchemy.url"),
        pool_pre_ping=True,
        future=True,
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=False,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
