"""In-memory LLM client for tests and local development.

Records every call it receives and returns scripted responses. Lives in
the production tree (not tests/) so any module can use it without importing
test code — useful for local runs without API credits.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.services.llm.base import LLMClient
from app.services.llm.schemas import LLMMessage, LLMResponse, LLMUsage


@dataclass
class RecordedCall:
    """One captured invocation of FakeLLMClient.complete."""

    messages: list[LLMMessage]
    system: str | None
    model: str | None
    max_tokens: int | None


@dataclass
class FakeLLMClient(LLMClient):
    """LLMClient that returns canned responses and records every call.

    Usage in tests:
        client = FakeLLMClient(responses=['{"clarity": "...", ...}'])
        result = await service.do_thing(client=client)
        assert client.calls[0].system == "expected system prompt"

    By default returns the same response indefinitely. Pass a list to cycle
    through scripted responses; raises IndexError if exhausted (tests should
    provide enough responses for the calls they trigger).
    """

    responses: list[str] = field(default_factory=lambda: [""])
    model_name: str = "fake-model"
    calls: list[RecordedCall] = field(default_factory=list)
    _cursor: int = 0

    async def complete(
        self,
        messages: Sequence[LLMMessage],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls.append(
            RecordedCall(
                messages=list(messages),
                system=system,
                model=model,
                max_tokens=max_tokens,
            )
        )

        # Use last response indefinitely once we run out of scripted ones.
        idx = min(self._cursor, len(self.responses) - 1)
        self._cursor += 1
        text = self.responses[idx]

        return LLMResponse(
            text=text,
            model=model or self.model_name,
            usage=LLMUsage(input_tokens=0, output_tokens=0),
            stop_reason="end_turn",
        )
