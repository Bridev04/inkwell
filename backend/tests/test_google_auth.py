"""Tests for GET /api/v1/auth/google and /api/v1/auth/google/callback.

All network calls to Google (token exchange, JWKS fetch, ID-token validation)
are mocked so no real credentials are needed.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.main import app
from app.services.auth_service import create_user

# ---------------------------------------------------------------------------
# Fixture: wire db_session into the app without a pre-created user
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="function")
async def google_db_session(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Wire db_session into the FastAPI dependency graph (no pre-created user)."""

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override
    try:
        yield db_session
    finally:
        app.dependency_overrides.pop(get_session, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_CLAIMS: dict[str, Any] = {
    "sub": "google-sub-abc123",
    "email": "guser@gmail.com",
    "email_verified": True,
    "name": "Google User",
    "iss": "https://accounts.google.com",
    "aud": "fake-client-id",
    "exp": 9999999999,
    "nonce": "test-nonce",
}

_FAKE_TOKEN_RESPONSE: dict[str, Any] = {
    "access_token": "ya29.fake",
    "id_token": "eyJhbGciOiJSUzI1NiJ9.fake.sig",
    "token_type": "Bearer",
}


def _patch_google(claims: dict[str, Any] | None = None) -> Any:
    """Context manager that mocks all Google network calls."""
    import contextlib

    @contextlib.contextmanager
    def _ctx() -> Generator[None, None, None]:
        with (
            patch(
                "app.services.google_oauth.exchange_code",
                new_callable=AsyncMock,
                return_value=_FAKE_TOKEN_RESPONSE,
            ),
            patch(
                "app.services.google_oauth.fetch_google_jwks",
                new_callable=AsyncMock,
                return_value={"keys": []},
            ),
            patch(
                "app.services.google_oauth.validate_id_token",
                return_value=claims or _FAKE_CLAIMS,
            ),
        ):
            yield

    return _ctx()


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _start_flow(client: AsyncClient) -> tuple[str, str]:
    """Hit /auth/google and return (state_query_param, signed_cookie_value)."""
    with patch("app.config.settings.google_client_id", "fake-client-id"):
        r = await client.get("/api/v1/auth/google?next=/desk", follow_redirects=False)
    assert r.status_code == 307
    location = r.headers["location"]
    # Extract state from Google auth URL
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(location).query)
    state = qs["state"][0]
    cookie_val = r.cookies.get("oauth_state") or ""
    return state, cookie_val


# ---------------------------------------------------------------------------
# /auth/google (start)
# ---------------------------------------------------------------------------


async def test_google_start_returns_307_and_sets_state_cookie(
    google_db_session: AsyncSession,
) -> None:
    async with _make_client() as ac:
        with patch("app.config.settings.google_client_id", "fake-client-id"):
            r = await ac.get("/api/v1/auth/google", follow_redirects=False)

    assert r.status_code == 307
    assert "accounts.google.com" in r.headers["location"]
    assert "oauth_state" in r.cookies


async def test_google_start_location_includes_pkce_and_state(
    google_db_session: AsyncSession,
) -> None:
    from urllib.parse import parse_qs, urlparse

    async with _make_client() as ac:
        with patch("app.config.settings.google_client_id", "fake-client-id"):
            r = await ac.get("/api/v1/auth/google", follow_redirects=False)

    qs = parse_qs(urlparse(r.headers["location"]).query)
    assert "state" in qs
    assert "nonce" in qs
    assert qs.get("code_challenge_method") == ["S256"]
    assert "code_challenge" in qs


async def test_google_start_503_when_unconfigured() -> None:
    async with _make_client() as ac:
        with patch("app.config.settings.google_client_id", None):
            r = await ac.get("/api/v1/auth/google", follow_redirects=False)
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# /auth/google/callback — state / cookie validation
# ---------------------------------------------------------------------------


async def test_callback_missing_code_returns_422(google_db_session: AsyncSession) -> None:
    async with _make_client() as ac:
        r = await ac.get("/api/v1/auth/google/callback?state=abc")
    assert r.status_code == 422


async def test_callback_missing_state_cookie_returns_400(google_db_session: AsyncSession) -> None:
    async with _make_client() as ac:
        r = await ac.get("/api/v1/auth/google/callback?code=abc&state=xyz")
    assert r.status_code == 400
    assert "cookie" in r.json()["detail"].lower()


async def test_callback_state_mismatch_returns_400(google_db_session: AsyncSession) -> None:
    from itsdangerous import URLSafeTimedSerializer

    from app.config import get_settings

    s = get_settings()
    serializer = URLSafeTimedSerializer(
        s.jwt_secret_key.get_secret_value(), salt="google-oauth-state"
    )
    valid_cookie = serializer.dumps(
        {"state": "real-state", "nonce": "n", "code_verifier": "v", "next": "/desk"}
    )

    async with _make_client() as ac:
        ac.cookies.set("oauth_state", valid_cookie, path="/api/v1/auth/google/callback")
        r = await ac.get("/api/v1/auth/google/callback?code=abc&state=WRONG-state")

    assert r.status_code == 400
    assert "mismatch" in r.json()["detail"].lower()


async def test_callback_error_param_returns_400(google_db_session: AsyncSession) -> None:
    async with _make_client() as ac:
        r = await ac.get("/api/v1/auth/google/callback?error=access_denied")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# /auth/google/callback — user creation / linking
# ---------------------------------------------------------------------------


async def _do_callback(
    session: AsyncSession,
    claims: dict[str, Any] | None = None,
) -> Any:
    """Drive a full callback flow with mocked Google services."""
    from itsdangerous import URLSafeTimedSerializer

    from app.config import get_settings

    s = get_settings()
    state_val = "test-state-123"
    serializer = URLSafeTimedSerializer(
        s.jwt_secret_key.get_secret_value(), salt="google-oauth-state"
    )
    cookie_val = serializer.dumps(
        {
            "state": state_val,
            "nonce": "test-nonce",
            "code_verifier": "test-verifier",
            "next": "/desk",
        }
    )

    async with _make_client() as ac:
        ac.cookies.set("oauth_state", cookie_val, path="/api/v1/auth/google/callback")
        with _patch_google(claims), patch("app.config.settings.google_client_id", "fake-client-id"):
            r = await ac.get(
                f"/api/v1/auth/google/callback?code=authcode&state={state_val}",
                follow_redirects=False,
            )
    return r


async def test_callback_creates_new_google_user(google_db_session: AsyncSession) -> None:
    r = await _do_callback(google_db_session)

    assert r.status_code == 302
    assert "access_token" in r.cookies
    assert r.headers["location"].endswith("/desk")

    from sqlalchemy import select

    from app.models.user import User

    result = await google_db_session.execute(select(User).where(User.email == "guser@gmail.com"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.google_sub == "google-sub-abc123"
    assert user.hashed_password is None


async def test_callback_links_to_existing_local_user(google_db_session: AsyncSession) -> None:
    # Pre-create a local user with the same email
    existing = await create_user(google_db_session, email="guser@gmail.com", password="pass1234!")
    await google_db_session.flush()

    r = await _do_callback(google_db_session)

    assert r.status_code == 302
    assert "access_token" in r.cookies

    await google_db_session.refresh(existing)
    assert existing.google_sub == "google-sub-abc123"
    assert existing.hashed_password is not None  # password unchanged


async def test_callback_blocks_link_when_email_unverified(google_db_session: AsyncSession) -> None:
    await create_user(google_db_session, email="guser@gmail.com", password="pass1234!")
    await google_db_session.flush()

    unverified_claims = {**_FAKE_CLAIMS, "email_verified": False}
    r = await _do_callback(google_db_session, claims=unverified_claims)

    assert r.status_code == 409


async def test_callback_returning_google_user(google_db_session: AsyncSession) -> None:
    # Pre-create a Google user (from a previous login)
    import uuid

    from app.models.user import User

    google_user = User(
        id=uuid.uuid4(),
        email="guser@gmail.com",
        hashed_password=None,
        google_sub="google-sub-abc123",
        is_active=True,
    )
    google_db_session.add(google_user)
    await google_db_session.flush()

    r = await _do_callback(google_db_session)

    assert r.status_code == 302
    assert "access_token" in r.cookies


# ---------------------------------------------------------------------------
# open-redirect protection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "next_val,expected",
    [
        ("/desk", "/desk"),
        ("/documents/abc", "/documents/abc"),
        ("https://evil.com", "/desk"),
        ("//evil.com", "/desk"),
        ("/login?x=../../etc", "/desk"),
        ("", "/desk"),
    ],
)
def test_safe_next(next_val: str, expected: str) -> None:
    from app.api.v1.google_auth import _safe_next

    assert _safe_next(next_val) == expected


# ---------------------------------------------------------------------------
# password login still works (and rejects Google-only users)
# ---------------------------------------------------------------------------


async def test_password_login_rejected_for_google_only_user(
    google_db_session: AsyncSession,
) -> None:
    """A Google-only user (hashed_password=None) cannot log in with a password."""
    import uuid

    from app.models.user import User

    google_user = User(
        id=uuid.uuid4(),
        email="googleonly@example.com",
        hashed_password=None,
        google_sub="sub-googleonly",
        is_active=True,
    )
    google_db_session.add(google_user)
    await google_db_session.flush()

    async with _make_client() as ac:
        r = await ac.post(
            "/api/v1/auth/login",
            json={"email": "googleonly@example.com", "password": "anypassword"},
        )
    assert r.status_code == 401


async def test_password_login_still_works_for_local_user(
    google_db_session: AsyncSession,
) -> None:
    await create_user(google_db_session, email="localuser@example.com", password="pass1234!")
    await google_db_session.flush()

    async with _make_client() as ac:
        r = await ac.post(
            "/api/v1/auth/login",
            json={"email": "localuser@example.com", "password": "pass1234!"},
        )
    assert r.status_code == 200
    assert "access_token" in r.cookies
