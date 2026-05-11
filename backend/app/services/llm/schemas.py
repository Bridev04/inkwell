"""Pydantic schemas for the provider-agnostic LLM layer.

These models define the contract between services and any LLM provider.
Concrete clients (Anthropic, OpenAI, fakes) translate to/from these types
at their boundaries — internal SDK types never leak into the rest of the app.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant"]


class LLMMessage(BaseModel):
    """A single message in an LLM conversation.

    System prompts are passed separately on the client call, mirroring
    the Anthropic Messages API shape, so they aren't represented here.
    """

    role: Role
    content: str = Field(min_length=1)


class LLMUsage(BaseModel):
    """Token accounting from a completion.

    Recorded so we can attribute cost per user once auth lands.
    """

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class LLMResponse(BaseModel):
    """Normalized response from any LLM provider."""

    text: str
    model: str
    usage: LLMUsage
    stop_reason: str | None = None
