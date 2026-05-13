"""Async database engine, session factory, and FastAPI dependency."""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


@lru_cache
def _engine() -> AsyncEngine:
    url = settings.database_url
    if url is None:
        raise RuntimeError("DATABASE_URL is not configured; add it to .env")
    # pool_size and max_overflow are connection pool tuning knobs.
    # Increase pool_size for higher sustained concurrency; max_overflow caps burst headroom.
    return create_async_engine(url, pool_size=5, max_overflow=10)


@lru_cache
def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a committed-on-success AsyncSession.

    Commit is deferred to request teardown so handlers can issue multiple
    operations without manual commit calls. Rolling back on any exception
    prevents partial writes from being visible.
    """
    session = _session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
