"""Tests for the health check endpoint."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP client that talks to the FastAPI app in-process.

    ASGITransport skips the network entirely — no server needed.
    Faster and more reliable than spinning up uvicorn for each test.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_returns_ok(client: AsyncClient) -> None:
    """Health check returns 200 with the expected payload shape."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Draftwell"
    assert "environment" in body


async def test_health_response_schema(client: AsyncClient) -> None:
    """Health response has exactly the documented fields — no leaks, no missing."""
    response = await client.get("/api/v1/health")

    assert set(response.json().keys()) == {"status", "app", "environment"}
