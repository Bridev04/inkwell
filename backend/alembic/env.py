"""Alembic environment — wires app settings and ORM metadata into the migration runner."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401 — registers all models on Base.metadata
from alembic import context
from app.config import settings
from app.db.base import Base

# Alembic Config object, giving access to alembic.ini values.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Use the sync psycopg v3 URL from settings.
# The app uses asyncpg; Alembic's synchronous runner requires a sync driver.
if settings.database_url_sync is None:
    raise RuntimeError("DATABASE_URL_SYNC is not configured; add it to .env")
config.set_main_option("sqlalchemy.url", settings.database_url_sync)


def run_migrations_offline() -> None:
    """Emit migration SQL to stdout without a live DB connection.

    Useful for generating SQL to review or apply in production via a DBA.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
