from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from contracts_platform.core.config import settings

engine = create_async_engine(settings.POSTGRES_DSN, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def get_fresh_session_factory() -> async_sessionmaker:
    """Create a fresh engine + session factory bound to the current event loop.
    Use this inside Celery tasks (asyncio.run()) to avoid stale pool errors."""
    fresh_engine = create_async_engine(
        settings.POSTGRES_DSN, echo=False, pool_pre_ping=True, pool_size=1, max_overflow=0
    )
    return async_sessionmaker(fresh_engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
