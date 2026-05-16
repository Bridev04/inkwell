"""Anthropic-backed LLM client.

Wraps the Anthropic Messages API behind the provider-agnostic LLMClient
Protocol. Only this module imports the Anthropic SDK; the rest of the app
talks to LLMClient.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence

import anthropic
from anthropic.types import MessageParam, TextBlock, ToolChoiceToolParam, ToolParam, ToolUseBlock
from pydantic import BaseModel

from app.config import Settings
from app.services.llm.base import LLMError
from app.services.llm.schemas import LLMMessage, LLMResponse, LLMUsage, StreamChunk, TokenUsage


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

    async def generate_structured(
        self,
        prompt: str,
        response_schema: type[BaseModel],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> tuple[BaseModel, TokenUsage, str]:
        """Force-call a single tool whose schema mirrors `response_schema`.

        The Anthropic tool-use feature guarantees the response matches the
        schema, so validation failures indicate a genuine schema mismatch
        rather than a formatting glitch.
        """
        effective_max_tokens = max_tokens if max_tokens is not None else self._max_tokens
        tool_name = response_schema.__name__
        tool: ToolParam = {
            "name": tool_name,
            "description": f"Return a structured {tool_name} object.",
            "input_schema": response_schema.model_json_schema(),
        }
        tool_choice: ToolChoiceToolParam = {"type": "tool", "name": tool_name}
        user_message: MessageParam = {"role": "user", "content": prompt}

        response = await self._client.messages.create(
            model=self._default_model,
            max_tokens=effective_max_tokens,
            messages=[user_message],
            system=system if system is not None else anthropic.Omit(),
            tools=[tool],
            tool_choice=tool_choice,
        )

        tool_block = next(
            (b for b in response.content if isinstance(b, ToolUseBlock)),
            None,
        )
        if tool_block is None:
            raise LLMError("No tool_use block in structured response")

        parsed = response_schema.model_validate(tool_block.input)
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )
        return parsed, usage, response.model

    async def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a completion, forwarding text deltas as they arrive."""
        user_message: MessageParam = {"role": "user", "content": prompt}
        async with self._client.messages.stream(
            model=self._default_model,
            max_tokens=self._max_tokens,
            messages=[user_message],
            system=system if system is not None else anthropic.Omit(),
        ) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(type="text", text=text)
            final = await stream.get_final_message()
            yield StreamChunk(
                type="done",
                tokens_used=TokenUsage(
                    input_tokens=final.usage.input_tokens,
                    output_tokens=final.usage.output_tokens,
                    total_tokens=final.usage.input_tokens + final.usage.output_tokens,
                ),
                model_used=final.model,
            )
