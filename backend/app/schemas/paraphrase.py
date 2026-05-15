"""Request and event schemas for the paraphrase endpoint."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.llm.schemas import TokenUsage


class ParaphraseMode(StrEnum):
    STANDARD = "standard"
    SIMPLER = "simpler"
    SHORTER = "shorter"
    ACADEMIC = "academic"
    CREATIVE = "creative"


class ParaphraseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    mode: ParaphraseMode = ParaphraseMode.STANDARD
    save: bool = False


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


class DocumentEvent(BaseModel):
    """Emitted after the stream completes and the paraphrase is successfully saved."""

    document_id: UUID
