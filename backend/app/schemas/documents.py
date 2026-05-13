"""Pydantic response schemas for the documents read endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FeedbackRead(BaseModel):
    id: uuid.UUID
    result: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class RewriteRead(BaseModel):
    id: uuid.UUID
    style: str
    output: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: uuid.UUID
    original_text: str
    created_at: datetime
    feedbacks: list[FeedbackRead]
    rewrites: list[RewriteRead]

    model_config = {"from_attributes": True}
