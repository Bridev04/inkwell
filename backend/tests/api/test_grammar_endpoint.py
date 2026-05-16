"""Integration tests for POST /api/v1/grammar.

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
from app.schemas.grammar import GrammarResponse
from app.services.grammar_service import _LLMGrammarPayload, _LLMIssueItem
from app.services.llm.fakes import FakeLLMClient


def _valid_payload() -> _LLMGrammarPayload:
    return _LLMGrammarPayload(
        issues=[
            _LLMIssueItem(
                category="grammar",
                original="walked",
                replacement="walk",
                short_label="Change verb tense",
                explanation="Present tense required.",
            )
        ]
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


async def test_post_grammar_returns_200_and_valid_schema() -> None:
    fake = FakeLLMClient(structured_responses=[_valid_payload()])
    async with _client_with(fake) as ac:
        response = await ac.post(
            "/api/v1/grammar",
            json={"text": "Yesterday I walked to school."},
        )

    assert response.status_code == 200
    body = GrammarResponse.model_validate(response.json())
    assert body.document_id is None
    assert len(body.issues) == 1
    assert body.issues[0].category.value == "grammar"
    assert body.issues[0].original == "walked"
    assert body.issues[0].replacement == "walk"
    assert body.issues[0].start >= 0
    assert body.issues[0].end > body.issues[0].start
    assert body.word_count == 5
    assert 0 <= body.scores.overall <= 100
    assert body.scores.overall_label in ("Needs work", "Fair", "Good", "Great")


async def test_post_grammar_empty_text_422() -> None:
    fake = FakeLLMClient(structured_responses=[_valid_payload()])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/grammar", json={"text": ""})
    assert response.status_code == 422


async def test_post_grammar_oversize_text_422() -> None:
    fake = FakeLLMClient(structured_responses=[_valid_payload()])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/grammar", json={"text": "x" * 10_001})
    assert response.status_code == 422


async def test_post_grammar_llm_timeout_504() -> None:
    timeout_err = anthropic.APITimeoutError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    fake = FakeLLMClient(structured_responses=[timeout_err])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/grammar", json={"text": "Some draft."})
    assert response.status_code == 504


async def test_post_grammar_rate_limit_429() -> None:
    rate_err = anthropic.RateLimitError(
        message="rate limited",
        response=httpx.Response(429, request=httpx.Request("POST", "https://api.anthropic.com")),
        body=None,
    )
    fake = FakeLLMClient(structured_responses=[rate_err])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/grammar", json={"text": "Some draft."})
    assert response.status_code == 429


async def test_post_grammar_no_issues_scores_100() -> None:
    """Empty issues list → all scores 100 and overall_label Great."""
    fake = FakeLLMClient(structured_responses=[_LLMGrammarPayload(issues=[])])
    async with _client_with(fake) as ac:
        response = await ac.post("/api/v1/grammar", json={"text": "A well written sentence."})

    assert response.status_code == 200
    body = GrammarResponse.model_validate(response.json())
    assert body.issues == []
    assert body.scores.overall == 100
    assert body.scores.overall_label == "Great"
