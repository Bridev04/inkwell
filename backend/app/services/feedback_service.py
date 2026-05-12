"""Business logic for the feedback endpoint.

Builds LLM prompts, calls generate_structured with a retry on validation
failure, and assembles the final FeedbackResponse.
"""

from __future__ import annotations

import logging
import time
from typing import cast
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from app.schemas.feedback import (
    DimensionFeedback,
    FeedbackRequest,
    FeedbackResponse,
)
from app.services.llm.base import LLMClient
from app.services.llm.schemas import TokenUsage

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert writing coach reviewing a draft submitted by a writer.

Score each dimension on a 1-5 scale:
  1 = serious issues that undermine the writing
  2 = noticeable weaknesses that distract the reader
  3 = competent — meets expectations, minor rough edges
  4 = strong — clear, intentional, well-executed
  5 = exceptional — polished, memorable, nothing to add

Observations describe what IS present in the draft (facts, not judgements).
Suggestions describe concrete changes the writer should make.
Keep each bullet to one short sentence.
"""


class _LLMFeedbackPayload(BaseModel):
    """Internal schema for the LLM tool-use response.

    Excludes fields the service fills in (request_id, model_used, tokens_used).
    """

    overall_summary: str
    dimensions: list[DimensionFeedback]
    suggested_rewrites: list[str] = Field(default_factory=list, max_length=3)


def _build_prompt(req: FeedbackRequest) -> str:
    focus_list = ", ".join(d.value for d in req.focus)
    lines = [
        f"Please review the following draft. Focus on: {focus_list}.",
    ]
    if req.audience:
        lines.append(f"Intended audience: {req.audience}.")
    lines.append("")
    lines.append("--- DRAFT START ---")
    lines.append(req.text)
    lines.append("--- DRAFT END ---")
    return "\n".join(lines)


async def generate_feedback(req: FeedbackRequest, llm: LLMClient) -> FeedbackResponse:
    """Generate structured writing feedback for the submitted draft.

    Retries once on ValidationError before propagating. All other exceptions
    (provider timeouts, rate limits) propagate immediately.
    """
    request_id = uuid4()
    start = time.monotonic()
    prompt = _build_prompt(req)

    result: tuple[BaseModel, TokenUsage, str] | None = None
    last_error: ValidationError | None = None

    for _ in range(2):
        try:
            result = await llm.generate_structured(
                prompt=prompt,
                response_schema=_LLMFeedbackPayload,
                system=_SYSTEM_PROMPT,
            )
            break
        except ValidationError as exc:
            logger.error(
                "Structured output failed validation; retrying",
                extra={"request_id": str(request_id)},
            )
            last_error = exc

    if result is None:
        if last_error is not None:
            raise last_error
        raise RuntimeError("generate_structured returned no result")  # unreachable

    raw, token_usage, model_name = result
    payload = cast(_LLMFeedbackPayload, raw)

    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "Feedback generated",
        extra={
            "request_id": str(request_id),
            "input_chars": len(req.text),
            "focus": [d.value for d in req.focus],
            "latency_ms": latency_ms,
            "input_tokens": token_usage.input_tokens,
            "output_tokens": token_usage.output_tokens,
            "model": model_name,
        },
    )

    return FeedbackResponse(
        request_id=request_id,
        overall_summary=payload.overall_summary,
        dimensions=payload.dimensions,
        suggested_rewrites=payload.suggested_rewrites,
        model_used=model_name,
        tokens_used=token_usage,
    )
