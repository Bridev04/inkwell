"""Provider-agnostic LLM client interface.

Defined as a Protocol rather than an ABC so that test doubles and future
providers can satisfy it structurally without inheritance. Concrete
implementations live alongside this file (anthropic_client.py, fakes.py).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from app.services.llm.schemas import LLMMessage, LLMResponse, StreamChunk, TokenUsage


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface for a chat-completion LLM provider."""

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

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[BaseModel],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> tuple[BaseModel, TokenUsage, str]:
        """Generate a completion and parse the response into a Pydantic model.

        Uses tool-use / function-calling to force the provider to emit a
        schema-conformant JSON object. The third element of the return tuple
        is the model identifier reported by the provider.

        Raises:
            pydantic.ValidationError: If the provider response fails schema validation
                after any provider-level retries. Callers may retry once.
            Provider-specific exceptions propagate unchanged so route handlers
                can map them to appropriate HTTP status codes.
        """
        ...

    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a completion as an async sequence of chunks.

        Yields zero or more ``type="text"`` chunks followed by exactly one
        ``type="done"`` chunk. Provider-specific exceptions propagate unchanged
        so route handlers can map pre-flight errors to HTTP status codes.
        """
        ...


class LLMError(Exception):
    """Raised by LLM clients on any provider-side failure.

    Wraps the underlying exception (available via `__cause__`) so callers
    can handle one error type regardless of provider.
    """
