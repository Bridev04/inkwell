"""FastAPI dependency providers shared across route modules."""

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.base import LLMClient


def get_llm_client(settings: Settings = Depends(get_settings)) -> LLMClient:  # noqa: B008
    """Provides a configured LLMClient for route handlers."""
    return AnthropicClient(settings)
