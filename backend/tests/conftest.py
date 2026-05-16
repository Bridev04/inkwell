"""Shared pytest fixtures, including testcontainers-based DB isolation.

Architecture:
  postgres_container  (session-scoped, sync)  — starts once, lives for the whole suite
  run_migrations      (session-scoped, sync)  — applies alembic upgrade head once
  db_session          (function-scoped, async) — per-test AsyncSession backed by a
                                                 transaction that is rolled back after
                                                 each test for isolation
  db_user             (function-scoped, async) — a real User row in db_session
  override_db_session (function-scoped, async) — db_session + db_user wired into the
                                                 FastAPI dependency graph for endpoint tests
"""

from __future__ import annotations

import pathlib
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from alembic import command
from app.api.deps import get_current_user
from app.db.session import get_session
from app.main import app
from app.models.user import User

_BACKEND_DIR = pathlib.Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Container lifecycle — starts Postgres once per test session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def postgres_container():  # type: ignore[return]
    """Start a Postgres 16 testcontainer for the whole test session.

    Session-scoped so the container (and its data) live across all test
    modules. The per-test transaction rollback in ``db_session`` provides
    isolation without restarting the container.

    Tests that depend on this fixture are skipped when Docker is not available.
    """
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers[postgres] not installed")

    # Verify Docker is reachable before trying to start a container.
    try:
        import docker as _docker

        _docker.from_env().ping()
    except Exception as exc:
        pytest.skip(f"Docker not available: {exc}")

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as container:
        yield container


@pytest.fixture(scope="session")
def db_urls(postgres_container: object) -> tuple[str, str]:
    """Return ``(async_url, sync_url)`` for the test container."""
    from testcontainers.postgres import PostgresContainer

    assert isinstance(postgres_container, PostgresContainer)
    raw = postgres_container.get_connection_url()
    # testcontainers returns postgresql+psycopg2:// by default
    async_url = raw.replace("+psycopg2", "+asyncpg")
    sync_url = raw.replace("+psycopg2", "+psycopg")
    return async_url, sync_url


@pytest.fixture(scope="session")
def run_migrations(db_urls: tuple[str, str]) -> None:
    """Run ``alembic upgrade head`` against the testcontainer once per session."""
    _, sync_url = db_urls
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")


# ---------------------------------------------------------------------------
# Per-test session with transaction rollback for isolation
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="function")
async def db_session(
    db_urls: tuple[str, str],
    run_migrations: None,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-test AsyncSession that is fully rolled back after the test.

    The session is bound to an outer transaction on the connection. Any
    ``session.commit()`` calls from code under test create savepoints rather
    than real commits, keeping the data invisible to other connections and
    allowing a clean rollback at teardown.
    """
    async_url, _ = db_urls
    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            await conn.begin()
            session = AsyncSession(
                bind=conn,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
            )
            try:
                yield session
            finally:
                await session.close()
                await conn.rollback()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def db_user(db_session: AsyncSession) -> User:
    """A real User row in db_session, usable as FK owner for documents."""
    from app.services.auth_service import create_user

    return await create_user(db_session, email="test@example.com", password="testpass123!")


@pytest_asyncio.fixture(loop_scope="function")
async def override_db_session(
    db_session: AsyncSession,
    db_user: User,
) -> AsyncGenerator[AsyncSession, None]:
    """Wire ``db_session`` and ``db_user`` into the FastAPI dependency graph.

    Use this fixture in endpoint tests that need real DB access so that
    the in-process test client hits the same rolled-back session as the
    direct service-layer assertions.
    """

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: db_user
    try:
        yield db_session
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_user, None)
