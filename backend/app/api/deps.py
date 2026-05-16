"""FastAPI dependency providers shared across route modules."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import get_user_by_id
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.base import LLMClient
from app.services.token_service import decode_access_token


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:  # noqa: B008
    """Provides a configured LLMClient for route handlers."""
    return AnthropicClient(settings)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> User:
    """Decode the access_token cookie and return the authenticated User."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id: uuid.UUID = decode_access_token(token, settings)
    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user
