"""Anthropic-backed LLM client.

Wraps the Anthropic Messages API behind the provider-agnostic LLMClient
Protocol. Only this module imports the Anthropic SDK; the rest of the app
talks to LLMClient.
"""

from __future__ import annotations

from collections.abc import Sequence

import anthropic
from anthropic.types import MessageParam, TextBlock

from app.config import Settings
from app.services.llm.base import LLMError
from app.services.llm.schemas import LLMMessage, LLMResponse, LLMUsage


class AnthropicClient:
    """LLMClient backed by the Anthropic Messages API.

    Instantiate once and reuse — the underlying SDK client manages its own
    connection pool. Pass settings at construction time so this class never
    reads env vars directly.
    """

    def __init__(self, settings: Settings) -> None:
        self._default_model = settings.llm_default_model
        self._max_tokens = settings.llm_max_tokens
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )

    async def complete(
        self,
        messages: Sequence[LLMMessage],
        *,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        effective_model = model if model is not None else self._default_model
        effective_max_tokens = max_tokens if max_tokens is not None else self._max_tokens

        sdk_messages: list[MessageParam] = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        try:
            response = await self._client.messages.create(
                model=effective_model,
                max_tokens=effective_max_tokens,
                messages=sdk_messages,
                system=system if system is not None else anthropic.Omit(),
            )
        except anthropic.APIError as exc:
            raise LLMError(str(exc)) from exc

        text = "".join(block.text for block in response.content if isinstance(block, TextBlock))

        return LLMResponse(
            text=text,
            model=response.model,
            usage=LLMUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            stop_reason=response.stop_reason,
        )
