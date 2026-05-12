"""Request and response schemas for the feedback endpoint."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.llm.schemas import TokenUsage


class FocusDimension(StrEnum):
    CLARITY = "clarity"
    TONE = "tone"
    STRUCTURE = "structure"


class FeedbackRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    focus: list[FocusDimension] = Field(default_factory=lambda: list(FocusDimension))
    audience: str | None = Field(default=None, max_length=200)


class DimensionFeedback(BaseModel):
    name: FocusDimension
    score: int = Field(ge=1, le=5)
    observations: list[str]
    suggestions: list[str]


class FeedbackResponse(BaseModel):
    request_id: UUID
    overall_summary: str
    dimensions: list[DimensionFeedback]
    suggested_rewrites: list[str] = Field(default_factory=list, max_length=3)
    model_used: str
    tokens_used: TokenUsage
