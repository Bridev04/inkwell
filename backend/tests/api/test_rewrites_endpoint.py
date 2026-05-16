"""Integration tests for POST /api/v1/rewrites.

All LLM calls are intercepted by FakeLLMClient via dependency override.
No network traffic in this test module.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anthropic
import httpx
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_llm_client
from app.main import app
from app.schemas.rewrite import DoneEvent, ErrorEvent
from app.services.llm.fakes import FakeLLMClient
from app.services.llm.schemas import StreamChunk, TokenUsage


def _text_chunk(text: str) -> StreamChunk:
    return StreamChunk(type="text", text=text)


def _done_chunk() -> StreamChunk:
    return StreamChunk(
        type="done",
        tokens_used=TokenUsage(input_tokens=5, output_tokens=10, total_tokens=15),
        model_used="fake-model",
    )


@asynccontextmanager
async def _client_with(fake: FakeLLMClient) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_llm_client] = lambda: fake
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_llm_client, None)


def _parse_events(text: str) -> list[dict[str, str]]:
    """Parse SSE text into a list of {event, data} dicts."""
    events: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("event:"):
            current["event"] = line[len("event:") :].strip()
        elif line.startswith("data:"):
            current["data"] = line[len("data:") :].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


async def test_post_rewrites_streams_tokens_and_done() -> None:
    fake = FakeLLMClient(
        stream_chunks=[_text_chunk("Hello "), _text_chunk("world."), _done_chunk()]
    )
    async with (
        _client_with(fake) as ac,
        ac.stream(
            "POST",
            "/api/v1/rewrites",
            json={"text": "Hi earth.", "style": "formal"},
        ) as response,
    ):
        body = await response.aread()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_events(body.decode())
    token_events = [e for e in events if e["event"] == "token"]
    done_events = [e for e in events if e["event"] == "done"]

    assert len(token_events) >= 1
    assert len(done_events) == 1

    done = DoneEvent.model_validate_json(done_events[0]["data"])
    assert done.tokens_used.total_tokens == 15
    assert done.latency_ms >= 0


async def test_post_rewrites_validates_empty_text() -> None:
    fake = FakeLLMClient()
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/rewrites", json={"text": "", "style": "casual"})
    assert response.status_code == 422


async def test_post_rewrites_validates_invalid_style() -> None:
    fake = FakeLLMClient()
    async with _client_with(fake) as ac:
        response = await ac.post(
            "/api/v1/rewrites", json={"text": "Some text.", "style": "shakespearean"}
        )
    assert response.status_code == 422


async def test_post_rewrites_returns_504_on_pre_flight_timeout() -> None:
    timeout_err = anthropic.APITimeoutError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    fake = FakeLLMClient(stream_chunks=[timeout_err])
    async with _client_with(fake) as ac:
        response = await ac.post(
            "/api/v1/rewrites", json={"text": "Some draft.", "style": "concise"}
        )
    assert response.status_code == 504
    assert response.headers.get("content-type", "").startswith("application/json")


async def test_post_rewrites_returns_429_on_pre_flight_rate_limit() -> None:
    rate_err = anthropic.RateLimitError(
        message="rate limited",
        response=httpx.Response(429, request=httpx.Request("POST", "https://api.anthropic.com")),
        body=None,
    )
    fake = FakeLLMClient(stream_chunks=[rate_err])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/rewrites", json={"text": "Some draft.", "style": "vivid"})
    assert response.status_code == 429


async def test_post_rewrites_emits_error_event_on_mid_stream_failure() -> None:
    fake = FakeLLMClient(
        stream_chunks=[
            _text_chunk("partial output"),
            RuntimeError("mid-stream failure"),
        ]
    )
    async with (
        _client_with(fake) as ac,
        ac.stream(
            "POST",
            "/api/v1/rewrites",
            json={"text": "Some draft.", "style": "persuasive"},
        ) as response,
    ):
        body = await response.aread()

    assert response.status_code == 200
    events = _parse_events(body.decode())
    event_names = [e["event"] for e in events]

    assert "token" in event_names
    assert "error" in event_names
    assert "done" not in event_names

    error_event = next(e for e in events if e["event"] == "error")
    err = ErrorEvent.model_validate_json(error_event["data"])
    assert err.request_id is not None
    assert err.message
