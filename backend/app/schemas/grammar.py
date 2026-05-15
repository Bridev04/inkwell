"""Request and response schemas for the grammar checker endpoint."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.llm.schemas import TokenUsage


class GrammarRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    save: bool = False


class GrammarIssue(BaseModel):
    type: Literal["grammar", "spelling", "punctuation", "style"]
    original: str
    suggestion: str
    explanation: str


class GrammarResponse(BaseModel):
    request_id: UUID
    issues: list[GrammarIssue]
    corrected_text: str
    overall_quality: Literal["Poor", "Fair", "Good", "Excellent"]
    model_used: str
    tokens_used: TokenUsage
    document_id: UUID | None = None
