"""Request and response schemas for the grammar checker endpoint."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class IssueCategory(StrEnum):
    grammar = "grammar"
    spelling = "spelling"
    punctuation = "punctuation"
    style = "style"


class GrammarRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    save: bool = False


class GrammarIssue(BaseModel):
    id: str
    category: IssueCategory
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    original: str
    replacement: str
    short_label: str
    explanation: str


class GrammarScores(BaseModel):
    grammar: int = Field(ge=0, le=100)
    spelling: int = Field(ge=0, le=100)
    punctuation: int = Field(ge=0, le=100)
    style: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)
    overall_label: Literal["Needs work", "Fair", "Good", "Great"]


class GrammarResponse(BaseModel):
    document_id: UUID | None = None
    corrected_text: str = ""
    issues: list[GrammarIssue]
    scores: GrammarScores
    word_count: int = Field(ge=0)
