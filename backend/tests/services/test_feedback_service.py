"""Tests for generate_feedback service function.

All LLM calls go through FakeLLMClient — no network traffic.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.feedback import (
    DimensionFeedback,
    FeedbackRequest,
    FocusDimension,
)
from app.services.feedback_service import _LLMFeedbackPayload, generate_feedback
from app.services.llm.fakes import FakeLLMClient


def _valid_payload() -> _LLMFeedbackPayload:
    return _LLMFeedbackPayload(
        overall_summary="Clear and well-structured piece.",
        dimensions=[
            DimensionFeedback(
                name=FocusDimension.CLARITY,
                score=4,
                observations=["Sentences are concise."],
                suggestions=["Consider adding a topic sentence to paragraph 2."],
            ),
        ],
        suggested_rewrites=["Consider starting with the conclusion."],
    )


def _make_validation_error() -> ValidationError:
    try:
        _LLMFeedbackPayload.model_validate({})
    except ValidationError as exc:
        return exc
    raise AssertionError("model_validate({}) should have raised")  # pragma: no cover


async def test_generate_feedback_happy_path() -> None:
    payload = _valid_payload()
    fake = FakeLLMClient(structured_responses=[payload])

    req = FeedbackRequest(text="This is my draft.")
    response = await generate_feedback(req, fake)

    assert response.request_id is not None
    assert response.overall_summary == payload.overall_summary
    assert len(response.dimensions) == 1
    assert response.dimensions[0].name == FocusDimension.CLARITY
    assert response.model_used == fake.model_name
    assert response.tokens_used.total_tokens == 30


async def test_generate_feedback_retries_on_validation_error() -> None:
    payload = _valid_payload()
    error = _make_validation_error()
    fake = FakeLLMClient(structured_responses=[error, payload])

    req = FeedbackRequest(text="Draft text here.")
    response = await generate_feedback(req, fake)

    assert response.overall_summary == payload.overall_summary
    assert fake._structured_cursor == 2  # both responses consumed


async def test_generate_feedback_raises_after_second_validation_failure() -> None:
    error = _make_validation_error()
    fake = FakeLLMClient(structured_responses=[error, error])

    req = FeedbackRequest(text="Draft text here.")
    with pytest.raises(ValidationError):
        await generate_feedback(req, fake)
