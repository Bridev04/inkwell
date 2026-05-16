"""Pydantic schemas for user registration, login, and responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(
        min_length=5,
        max_length=255,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}
