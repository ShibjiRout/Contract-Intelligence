"""Alembic async env.py — uses the SQLAlchemy engine from the application client."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncConnection

from contracts_platform.db.postgresql.client import engine
from contracts_platform.db.postgresql.models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection)."""
    url = engine.url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations against the async engine."""
    async with engine.begin() as conn:
        await conn.run_sync(_run_migrations_sync)


def _run_migrations_sync(conn: AsyncConnection) -> None:
    context.configure(connection=conn, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
