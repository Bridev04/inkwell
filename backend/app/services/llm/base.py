"""Provider-agnostic LLM client interface.

Defined as a Protocol rather than an ABC so that test doubles and future
providers can satisfy it structurally without inheritance. Concrete
implementations live alongside this file (anthropic_client.py, fakes.py).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.services.llm.schemas import LLMMessage, LLMResponse


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface for a chat-completion LLM provider.

    Streaming is intentionally omitted from v1 — it will be added as a
    separate method (`stream`) when the frontend needs it, so synchronous
    callers don't have to deal with async iterators.
    """

    async def complete(
        self,
        messages: Sequence[LLMMessage],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a single completion.

        Args:
            messages: Conversation history. Must be non-empty and end with a user turn.
            system: Optional system prompt. Provider-level, not part of `messages`.
            model: Override the client's default model. Use `None` to accept the default.
            max_tokens: Override the client's default cap. Use `None` for the default.

        Returns:
            A normalized LLMResponse. Providers translate their native types into this.

        Raises:
            LLMError: On any provider-side failure (network, rate limit, invalid request).
                Callers should not need to catch provider-specific exceptions.
        """
        ...


class LLMError(Exception):
    """Raised by LLM clients on any provider-side failure.

    Wraps the underlying exception (available via `__cause__`) so callers
    can handle one error type regardless of provider.
    """
