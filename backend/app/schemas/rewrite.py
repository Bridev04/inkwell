"""Request and event schemas for the rewrites endpoint."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.llm.schemas import TokenUsage


class RewriteStyle(StrEnum):
    FORMAL = "formal"
    CASUAL = "casual"
    PERSUASIVE = "persuasive"
    CONCISE = "concise"
    VIVID = "vivid"


class RewriteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    style: RewriteStyle
    audience: str | None = Field(default=None, max_length=200)


class TokenEvent(BaseModel):
    """Emitted for each chunk of generated text."""

    text: str


class DoneEvent(BaseModel):
    """Emitted once at the end of a successful stream."""

    request_id: UUID
    model_used: str
    tokens_used: TokenUsage
    latency_ms: int


class ErrorEvent(BaseModel):
    """Emitted if generation fails mid-stream."""

    request_id: UUID
    message: str
