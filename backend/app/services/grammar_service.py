"""Business logic for the grammar checker endpoint.

Builds LLM prompts, calls generate_structured with a retry on validation
failure, and assembles the final GrammarResponse.
"""

from __future__ import annotations

import logging
import time
from typing import Literal, cast
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from app.schemas.grammar import GrammarIssue, GrammarRequest, GrammarResponse
from app.services.llm.base import LLMClient
from app.services.llm.schemas import TokenUsage

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a meticulous copy-editor checking a draft for errors.

Identify every grammar, spelling, punctuation, and style issue. For each issue:
  - type: one of "grammar", "spelling", "punctuation", "style"
  - original: the exact problematic text from the draft (keep it short — a word or phrase)
  - suggestion: the corrected replacement
  - explanation: one concise sentence explaining why it is wrong

Also produce:
  - corrected_text: the full draft with ALL issues fixed
  - overall_quality: one of "Poor", "Fair", "Good", "Excellent" based on the number and severity of issues

If the text has no issues, return an empty issues list and overall_quality "Excellent".
"""


class _LLMGrammarPayload(BaseModel):
    """Internal schema for the LLM tool-use response."""

    issues: list[GrammarIssue] = Field(default_factory=list)
    corrected_text: str
    overall_quality: Literal["Poor", "Fair", "Good", "Excellent"]


def _build_prompt(req: GrammarRequest) -> str:
    lines = [
        "Please check the following text for grammar, spelling, punctuation, and style issues.",
        "",
        "--- TEXT START ---",
        req.text,
        "--- TEXT END ---",
    ]
    return "\n".join(lines)


async def check_grammar(req: GrammarRequest, llm: LLMClient) -> GrammarResponse:
    """Run a grammar check on the submitted text.

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
                response_schema=_LLMGrammarPayload,
                system=_SYSTEM_PROMPT,
            )
            break
        except ValidationError as exc:
            logger.error(
                "Grammar structured output failed validation; retrying",
                extra={"request_id": str(request_id)},
            )
            last_error = exc

    if result is None:
        if last_error is not None:
            raise last_error
        raise RuntimeError("generate_structured returned no result")  # unreachable

    raw, token_usage, model_name = result
    payload = cast(_LLMGrammarPayload, raw)

    latency_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "Grammar check completed",
        extra={
            "request_id": str(request_id),
            "input_chars": len(req.text),
            "issue_count": len(payload.issues),
            "quality": payload.overall_quality,
            "latency_ms": latency_ms,
            "input_tokens": token_usage.input_tokens,
            "output_tokens": token_usage.output_tokens,
            "model": model_name,
        },
    )

    return GrammarResponse(
        request_id=request_id,
        issues=payload.issues,
        corrected_text=payload.corrected_text,
        overall_quality=payload.overall_quality,
        model_used=model_name,
        tokens_used=token_usage,
    )
