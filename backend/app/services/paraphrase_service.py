"""Business logic for the paraphrase endpoint.

Builds the LLM prompt, streams tokens, and formats each chunk as an SSE
event string. Pre-flight provider errors propagate to the route; mid-stream
errors are caught here and emitted as ``error`` SSE events so the HTTP
response (already started) remains valid.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sse import format_sse
from app.schemas.paraphrase import (
    DocumentEvent,
    DoneEvent,
    ErrorEvent,
    ParaphraseRequest,
    TokenEvent,
)
from app.services.llm.base import LLMClient
from app.services.llm.schemas import TokenUsage
from app.services.persistence import save_paraphrase

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a skilled editor paraphrasing text on request.

Mode definitions:
  standard: rephrase clearly in your own words, preserving the meaning and approximate length
  simpler: use plain everyday language, short sentences, avoid jargon — aim for a 6th-grade reading level
  shorter: cut to the essential idea; aim for ~60% of the original length, no filler
  academic: formal scholarly tone, precise vocabulary, passive voice where appropriate, third-person perspective
  creative: inventive phrasing, varied sentence rhythm, vivid word choices — keep the core meaning but make it memorable

CRITICAL: Return ONLY the paraphrased prose. No preamble, no commentary, \
no "Here is the paraphrase:" lead-in. No markdown formatting unless the original had it.
"""


def _build_prompt(req: ParaphraseRequest) -> str:
    lines = [f"Paraphrase the following text in {req.mode.value} mode."]
    lines.append("")
    lines.append("--- TEXT START ---")
    lines.append(req.text)
    lines.append("--- TEXT END ---")
    return "\n".join(lines)


async def stream_paraphrase(
    req: ParaphraseRequest,
    llm: LLMClient,
    session: AsyncSession | None = None,
    user_id: UUID | None = None,
) -> AsyncGenerator[str, None]:
    """Yield fully-formatted SSE event strings for a single paraphrase request.

    Pre-flight provider errors (raised before the first chunk) propagate
    unchanged so the route can map them to HTTP status codes. Mid-stream
    errors are caught and emitted as ``error`` SSE events.

    When ``session`` is provided and ``req.save`` is True, the full output is
    accumulated and persisted after the stream completes, followed by a
    ``document`` SSE event carrying the new document id.
    """
    request_id: UUID = uuid4()
    start = time.perf_counter()
    prompt = _build_prompt(req)
    tokens_used: TokenUsage | None = None
    output_chunks: list[str] = []

    chunks = llm.generate_stream(prompt=prompt, system=_SYSTEM_PROMPT)

    # Pre-flight: any provider error on the first chunk propagates to the route.
    try:
        first_chunk = await chunks.__anext__()
    except (anthropic.APITimeoutError, anthropic.RateLimitError, anthropic.APIError):
        raise

    output_chunks.append(first_chunk.text or "")
    yield format_sse("token", TokenEvent(text=first_chunk.text or ""))

    stream_failed = False
    done_emitted = False
    try:
        async for chunk in chunks:
            if chunk.type == "text":
                text = chunk.text or ""
                output_chunks.append(text)
                yield format_sse("token", TokenEvent(text=text))
            elif chunk.type == "done":
                done_emitted = True
                tokens_used = chunk.tokens_used
                latency_ms = int((time.perf_counter() - start) * 1000)
                yield format_sse(
                    "done",
                    DoneEvent(
                        request_id=request_id,
                        model_used=chunk.model_used or "unknown",
                        tokens_used=tokens_used
                        or TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                        latency_ms=latency_ms,
                    ),
                )
                logger.info(
                    "Paraphrase completed",
                    extra={
                        "request_id": str(request_id),
                        "input_chars": len(req.text),
                        "mode": req.mode.value,
                        "latency_ms": latency_ms,
                        "tokens_used": tokens_used.total_tokens if tokens_used else None,
                        "outcome": "success",
                    },
                )

        # Guard: emit a done event if the stream ended without one (e.g. network truncation).
        if not done_emitted and not stream_failed:
            latency_ms = int((time.perf_counter() - start) * 1000)
            yield format_sse(
                "done",
                DoneEvent(
                    request_id=request_id,
                    model_used="unknown",
                    tokens_used=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                    latency_ms=latency_ms,
                ),
            )
    except Exception as exc:
        stream_failed = True
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            "Paraphrase stream error",
            extra={
                "request_id": str(request_id),
                "input_chars": len(req.text),
                "mode": req.mode.value,
                "latency_ms": latency_ms,
                "outcome": "error",
            },
            exc_info=exc,
        )
        yield format_sse(
            "error",
            ErrorEvent(
                request_id=request_id,
                message="An error occurred while generating the paraphrase.",
            ),
        )

    if stream_failed or not req.save or session is None or user_id is None:
        return

    try:
        doc_id = await save_paraphrase(
            session,
            original_text=req.text,
            mode=req.mode.value,
            output="".join(output_chunks),
            user_id=user_id,
        )
        yield format_sse("document", DocumentEvent(document_id=doc_id))
    except Exception as exc:
        logger.error(
            "Failed to persist paraphrase",
            extra={"request_id": str(request_id)},
            exc_info=exc,
        )
        yield format_sse(
            "error",
            ErrorEvent(
                request_id=request_id,
                message="The paraphrase was generated but could not be saved.",
            ),
        )
