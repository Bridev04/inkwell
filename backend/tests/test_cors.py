"""CORS header tests — verifies the middleware is wired correctly.

These tests do not need a real DB or LLM client; they only exercise
the HTTP layer, so they are fast and always run (no Docker required).
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app

_ALLOWED_ORIGIN = "http://localhost:3000"
_HEALTH_URL = "/api/v1/health"


async def test_cors_preflight_returns_allow_origin() -> None:
    """OPTIONS preflight for an allowed origin must echo the origin back."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.options(
            _HEALTH_URL,
            headers={
                "Origin": _ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.headers.get("access-control-allow-origin") == _ALLOWED_ORIGIN


async def test_cors_simple_request_echoes_allow_origin() -> None:
    """A credentialed GET from an allowed origin must receive the ACAO header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(_HEALTH_URL, headers={"Origin": _ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == _ALLOWED_ORIGIN


async def test_cors_unlisted_origin_is_blocked() -> None:
    """Requests from an origin not in the allowlist must NOT receive the ACAO header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(_HEALTH_URL, headers={"Origin": "http://evil.example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
