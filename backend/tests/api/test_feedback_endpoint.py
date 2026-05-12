"""Integration tests for POST /api/v1/feedback.

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
from app.schemas.feedback import DimensionFeedback, FeedbackResponse, FocusDimension
from app.services.feedback_service import _LLMFeedbackPayload
from app.services.llm.fakes import FakeLLMClient


def _valid_payload() -> _LLMFeedbackPayload:
    return _LLMFeedbackPayload(
        overall_summary="Solid draft with room to improve transitions.",
        dimensions=[
            DimensionFeedback(
                name=FocusDimension.CLARITY,
                score=3,
                observations=["Main argument is stated early."],
                suggestions=["Break the third paragraph into two shorter ones."],
            ),
        ],
        suggested_rewrites=[],
    )


@asynccontextmanager
async def _client_with(fake: FakeLLMClient) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_llm_client] = lambda: fake
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


async def test_post_feedback_returns_200_and_valid_schema() -> None:
    fake = FakeLLMClient(structured_responses=[_valid_payload()])
    async with _client_with(fake) as ac:
        response = await ac.post(
            "/api/v1/feedback",
            json={"text": "My draft paragraph goes here."},
        )

    assert response.status_code == 200
    body = FeedbackResponse.model_validate(response.json())
    assert body.overall_summary == "Solid draft with room to improve transitions."
    assert len(body.dimensions) == 1
    assert body.tokens_used.total_tokens == 30


async def test_post_feedback_validates_empty_text() -> None:
    fake = FakeLLMClient(structured_responses=[_valid_payload()])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/feedback", json={"text": ""})
    assert response.status_code == 422


async def test_post_feedback_validates_oversize_text() -> None:
    fake = FakeLLMClient(structured_responses=[_valid_payload()])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/feedback", json={"text": "x" * 10_001})
    assert response.status_code == 422


async def test_post_feedback_handles_llm_timeout() -> None:
    timeout_err = anthropic.APITimeoutError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    fake = FakeLLMClient(structured_responses=[timeout_err])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/feedback", json={"text": "Some draft."})
    assert response.status_code == 504


async def test_post_feedback_handles_rate_limit() -> None:
    rate_err = anthropic.RateLimitError(
        message="rate limited",
        response=httpx.Response(429, request=httpx.Request("POST", "https://api.anthropic.com")),
        body=None,
    )
    fake = FakeLLMClient(structured_responses=[rate_err])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/feedback", json={"text": "Some draft."})
    assert response.status_code == 429
