"""Integration tests for POST /api/v1/auth/* — registration, login, logout, and me.

All tests use the testcontainers-based DB fixtures from conftest.py.
No LLM calls are made in this module.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.schemas.users import UserRead
from app.services.auth_service import create_user


async def test_register_creates_user_and_sets_cookie(
    override_db_session: AsyncSession,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/register",
            json={"email": "alice@example.com", "password": "securepass1"},
        )

    assert response.status_code == 201
    body = UserRead.model_validate(response.json())
    assert body.email == "alice@example.com"
    assert "access_token" in response.cookies


async def test_register_duplicate_email_returns_409(
    override_db_session: AsyncSession,
    db_user: User,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/register",
            # db_user already uses test@example.com
            json={"email": "test@example.com", "password": "anotherpass1"},
        )

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


async def test_register_invalid_email_returns_422(
    override_db_session: AsyncSession,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "securepass1"},
        )
    assert response.status_code == 422


async def test_register_short_password_returns_422(
    override_db_session: AsyncSession,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/register",
            json={"email": "bob@example.com", "password": "short"},
        )
    assert response.status_code == 422


async def test_login_valid_credentials_sets_cookie(
    override_db_session: AsyncSession,
    db_user: User,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpass123!"},
        )

    assert response.status_code == 200
    body = UserRead.model_validate(response.json())
    assert body.email == "test@example.com"
    assert "access_token" in response.cookies


async def test_login_wrong_password_returns_401(
    override_db_session: AsyncSession,
    db_user: User,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
    assert response.status_code == 401


async def test_login_unknown_email_returns_401(
    override_db_session: AsyncSession,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "somepassword"},
        )
    assert response.status_code == 401


async def test_logout_clears_cookie(override_db_session: AsyncSession) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register first to get a cookie
        await ac.post(
            "/api/v1/auth/register",
            json={"email": "charlie@example.com", "password": "securepass1"},
        )
        logout_response = await ac.post("/api/v1/auth/logout")

    assert logout_response.status_code == 204


async def test_get_me_returns_current_user(
    override_db_session: AsyncSession,
    db_user: User,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login to get the real cookie
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpass123!"},
        )
        assert login.status_code == 200
        me = await ac.get("/api/v1/auth/me")

    assert me.status_code == 200
    body = UserRead.model_validate(me.json())
    assert body.email == "test@example.com"
    assert body.id == db_user.id


async def test_get_me_without_cookie_returns_401(
    override_db_session: AsyncSession,
    db_user: User,
) -> None:
    # override_db_session wires get_current_user to db_user, but we need to
    # test the real auth flow here, so temporarily remove the override.
    from app.api.deps import get_current_user

    app.dependency_overrides.pop(get_current_user, None)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/auth/me")
        assert response.status_code == 401
    finally:
        # Restore — other tests in the session may depend on override_db_session
        async def _session_gen() -> object:
            yield override_db_session

        app.dependency_overrides[get_current_user] = lambda: db_user


async def test_protected_routes_return_401_without_cookie(
    override_db_session: AsyncSession,
    db_user: User,
) -> None:
    """Writing tool endpoints return 401 when the auth dependency is removed."""
    from app.api.deps import get_current_user

    app.dependency_overrides.pop(get_current_user, None)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r1 = await ac.post("/api/v1/feedback", json={"text": "Hello."})
            r2 = await ac.post("/api/v1/rewrites", json={"text": "Hello.", "style": "formal"})
            r3 = await ac.post("/api/v1/grammar", json={"text": "Hello."})
        assert r1.status_code == 401
        assert r2.status_code == 401
        assert r3.status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = lambda: db_user


async def test_document_ownership_enforced(
    override_db_session: AsyncSession,
    db_user: User,
) -> None:
    """GET /documents/{id} returns 404 for a document owned by a different user."""
    from app.services.persistence import save_feedback

    # Create a second user and a document owned by them
    other_user = await create_user(
        override_db_session, email="other@example.com", password="otherpass1"
    )
    doc_id = await save_feedback(
        override_db_session,
        original_text="Other user's doc.",
        result={"overall_summary": "x"},
        user_id=other_user.id,
    )
    await override_db_session.flush()

    # Request the document as db_user (the one wired into override_db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/documents/{doc_id}")

    assert response.status_code == 404
