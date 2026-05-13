"""Integration tests for the persistence service layer and document endpoint.

All tests use the testcontainers-based DB fixtures from conftest.py.
Each test runs in a transaction that is rolled back at teardown.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_llm_client
from app.main import app
from app.schemas.feedback import DimensionFeedback, FeedbackResponse, FocusDimension
from app.services.feedback_service import _LLMFeedbackPayload
from app.services.llm.fakes import FakeLLMClient
from app.services.llm.schemas import StreamChunk, TokenUsage
from app.services.persistence import get_document, save_feedback, save_rewrite


# ---------------------------------------------------------------------------
# Smoke: service layer round-trip
# ---------------------------------------------------------------------------


async def test_save_and_fetch_feedback(db_session: AsyncSession) -> None:
    """Save a document+feedback and verify all fields round-trip correctly."""
    result = {"overall_summary": "Good draft", "dimensions": [], "suggested_rewrites": []}
    doc_id = await save_feedback(db_session, original_text="My essay.", result=result)

    doc = await get_document(db_session, doc_id)
    assert doc is not None
    assert doc.original_text == "My essay."
    assert len(doc.feedbacks) == 1
    assert doc.feedbacks[0].result["overall_summary"] == "Good draft"
    assert doc.rewrites == []


async def test_save_and_fetch_rewrite(db_session: AsyncSession) -> None:
    """Save a document+rewrite and verify all fields round-trip correctly."""
    doc_id = await save_rewrite(
        db_session, original_text="Hello world.", style="formal", output="Greetings, globe."
    )

    doc = await get_document(db_session, doc_id)
    assert doc is not None
    assert doc.original_text == "Hello world."
    assert len(doc.rewrites) == 1
    assert doc.rewrites[0].style == "formal"
    assert doc.rewrites[0].output == "Greetings, globe."
    assert doc.feedbacks == []


async def test_get_document_returns_none_for_unknown_id(db_session: AsyncSession) -> None:
    doc = await get_document(db_session, uuid.uuid4())
    assert doc is None


# ---------------------------------------------------------------------------
# Feedback endpoint with save=True
# ---------------------------------------------------------------------------


def _valid_payload() -> _LLMFeedbackPayload:
    return _LLMFeedbackPayload(
        overall_summary="Solid draft.",
        dimensions=[
            DimensionFeedback(
                name=FocusDimension.CLARITY,
                score=4,
                observations=["Clear opening."],
                suggestions=["Tighten the conclusion."],
            )
        ],
        suggested_rewrites=[],
    )


async def test_feedback_save_true_returns_document_id(
    override_db_session: AsyncSession,
) -> None:
    """POST /feedback with save=True persists the result and returns document_id."""
    fake = FakeLLMClient(structured_responses=[_valid_payload()])
    app.dependency_overrides[get_llm_client] = lambda: fake

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/feedback",
            json={"text": "My draft.", "save": True},
        )

    app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 200
    body = FeedbackResponse.model_validate(response.json())
    assert body.document_id is not None

    # Verify the row landed in the DB
    doc = await get_document(override_db_session, body.document_id)
    assert doc is not None
    assert doc.original_text == "My draft."
    assert len(doc.feedbacks) == 1


async def test_feedback_save_false_returns_no_document_id(
    override_db_session: AsyncSession,
) -> None:
    """POST /feedback without save flag returns no document_id (default behaviour)."""
    fake = FakeLLMClient(structured_responses=[_valid_payload()])
    app.dependency_overrides[get_llm_client] = lambda: fake

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/feedback",
            json={"text": "My draft."},
        )

    app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 200
    body = FeedbackResponse.model_validate(response.json())
    assert body.document_id is None


# ---------------------------------------------------------------------------
# Rewrites endpoint with save=True
# ---------------------------------------------------------------------------


def _text_chunk(text: str) -> StreamChunk:
    return StreamChunk(type="text", text=text)


def _done_chunk() -> StreamChunk:
    return StreamChunk(
        type="done",
        tokens_used=TokenUsage(input_tokens=5, output_tokens=10, total_tokens=15),
        model_used="fake-model",
    )


def _parse_events(text: str) -> list[dict[str, str]]:
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


async def test_rewrites_save_true_emits_document_event(
    override_db_session: AsyncSession,
) -> None:
    """POST /rewrites with save=True emits a document SSE event and persists the row."""
    import json

    fake = FakeLLMClient(
        stream_chunks=[_text_chunk("Greetings, globe."), _done_chunk()]
    )
    app.dependency_overrides[get_llm_client] = lambda: fake

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with ac.stream(
            "POST",
            "/api/v1/rewrites",
            json={"text": "Hello world.", "style": "formal", "save": True},
        ) as response:
            body = await response.aread()

    app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 200
    events = _parse_events(body.decode())
    event_names = [e["event"] for e in events]

    assert "token" in event_names
    assert "done" in event_names
    assert "document" in event_names

    doc_event = next(e for e in events if e["event"] == "document")
    doc_id = uuid.UUID(json.loads(doc_event["data"])["document_id"])

    doc = await get_document(override_db_session, doc_id)
    assert doc is not None
    assert doc.original_text == "Hello world."
    assert len(doc.rewrites) == 1
    assert doc.rewrites[0].style == "formal"


# ---------------------------------------------------------------------------
# GET /documents/{id} endpoint
# ---------------------------------------------------------------------------


async def test_get_document_endpoint_returns_embedded_relations(
    override_db_session: AsyncSession,
) -> None:
    doc_id = await save_feedback(
        override_db_session,
        original_text="Endpoint test.",
        result={"overall_summary": "Test"},
    )
    await override_db_session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/documents/{doc_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(doc_id)
    assert data["original_text"] == "Endpoint test."
    assert len(data["feedbacks"]) == 1
    assert data["rewrites"] == []


async def test_get_document_endpoint_returns_404_for_unknown_id(
    override_db_session: AsyncSession,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "12345", "abc"])
async def test_get_document_endpoint_rejects_malformed_id(
    override_db_session: AsyncSession, bad_id: str
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/documents/{bad_id}")
    assert response.status_code == 422
