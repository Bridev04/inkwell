"""Tests for stream_rewrite service function.

All LLM calls go through FakeLLMClient — no network traffic.
"""

from __future__ import annotations

import httpx
import pytest
import anthropic

from app.schemas.rewrite import DoneEvent, ErrorEvent, RewriteRequest, RewriteStyle, TokenEvent
from app.services.llm.fakes import FakeLLMClient
from app.services.llm.schemas import StreamChunk, TokenUsage
from app.services.rewrite_service import stream_rewrite


def _done_chunk() -> StreamChunk:
    return StreamChunk(
        type="done",
        tokens_used=TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        model_used="fake-model",
    )


def _text_chunk(text: str) -> StreamChunk:
    return StreamChunk(type="text", text=text)


def _make_request(style: RewriteStyle = RewriteStyle.FORMAL) -> RewriteRequest:
    return RewriteRequest(text="Hello world.", style=style)


async def _collect_events(req: RewriteRequest, fake: FakeLLMClient) -> list[tuple[str, str]]:
    """Run the generator and return [(event_name, json_data), ...] pairs."""
    events: list[tuple[str, str]] = []
    gen = stream_rewrite(req, fake)
    async for sse in gen:
        for line in sse.splitlines():
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                events.append((event_name, line[len("data:"):].strip()))
    return events


async def test_stream_rewrite_yields_tokens_then_done() -> None:
    fake = FakeLLMClient(
        stream_chunks=[
            _text_chunk("chunk one "),
            _text_chunk("chunk two "),
            _text_chunk("chunk three"),
            _done_chunk(),
        ]
    )
    req = _make_request()
    events = await _collect_events(req, fake)

    assert len(events) == 4
    assert all(name == "token" for name, _ in events[:3])
    assert events[3][0] == "done"

    token_texts = [TokenEvent.model_validate_json(data).text for _, data in events[:3]]
    assert token_texts == ["chunk one ", "chunk two ", "chunk three"]

    done = DoneEvent.model_validate_json(events[3][1])
    assert done.tokens_used.total_tokens == 30
    assert done.model_used == "fake-model"
    assert done.latency_ms >= 0


async def test_stream_rewrite_emits_error_event_on_mid_stream_failure() -> None:
    fake = FakeLLMClient(
        stream_chunks=[
            _text_chunk("alpha "),
            _text_chunk("beta "),
            RuntimeError("simulated mid-stream failure"),
        ]
    )
    req = _make_request()
    events = await _collect_events(req, fake)

    assert len(events) == 3
    assert events[0][0] == "token"
    assert events[1][0] == "token"
    assert events[2][0] == "error"

    err = ErrorEvent.model_validate_json(events[2][1])
    assert err.request_id is not None
    assert err.message  # safe user-facing message present


async def test_stream_rewrite_propagates_pre_flight_errors() -> None:
    timeout_err = anthropic.APITimeoutError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    fake = FakeLLMClient(stream_chunks=[timeout_err])
    req = _make_request()

    with pytest.raises(anthropic.APITimeoutError):
        async for _ in stream_rewrite(req, fake):
            pass
