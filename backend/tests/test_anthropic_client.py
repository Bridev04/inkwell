"""Tests for AnthropicClient — all SDK calls are mocked, no network traffic."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest
from anthropic.types import TextBlock

from app.config import Settings
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.base import LLMError
from app.services.llm.schemas import LLMMessage


def _make_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "anthropic_api_key": "test-key",
        "llm_default_model": "claude-test-model",
        "llm_max_tokens": 512,
    }
    base.update(overrides)
    return Settings.model_validate(base)


def _make_sdk_response(
    texts: list[str],
    model: str = "claude-test-model",
    input_tokens: int = 10,
    output_tokens: int = 5,
    stop_reason: str = "end_turn",
) -> MagicMock:
    """Build a fake Anthropic SDK Message response."""
    blocks = [TextBlock(type="text", text=t) for t in texts]
    response = MagicMock()
    response.content = blocks
    response.model = model
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    response.stop_reason = stop_reason
    return response


@pytest.fixture
def mock_sdk() -> Generator[tuple[MagicMock, MagicMock], None, None]:
    """Patches anthropic.AsyncAnthropic and returns (mock_class, mock_instance)."""
    with patch("anthropic.AsyncAnthropic") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        mock_instance.messages.create = AsyncMock()
        yield mock_cls, mock_instance


async def test_complete_translates_messages_to_sdk(
    mock_sdk: tuple[MagicMock, MagicMock],
) -> None:
    """complete() passes model, max_tokens, messages, and system to the SDK."""
    _, mock_instance = mock_sdk
    mock_instance.messages.create.return_value = _make_sdk_response(["response"])

    client = AnthropicClient(_make_settings())
    await client.complete(
        [LLMMessage(role="user", content="hello")],
        system="be concise",
        model="claude-override",
        max_tokens=200,
    )

    mock_instance.messages.create.assert_called_once_with(
        model="claude-override",
        max_tokens=200,
        messages=[{"role": "user", "content": "hello"}],
        system="be concise",
    )


async def test_complete_maps_sdk_response_to_llm_response(
    mock_sdk: tuple[MagicMock, MagicMock],
) -> None:
    """complete() returns a properly populated LLMResponse."""
    _, mock_instance = mock_sdk
    mock_instance.messages.create.return_value = _make_sdk_response(
        ["Great article!"],
        model="claude-haiku-4-5-20251001",
        input_tokens=42,
        output_tokens=7,
        stop_reason="end_turn",
    )

    client = AnthropicClient(_make_settings())
    result = await client.complete([LLMMessage(role="user", content="Review this.")])

    assert result.text == "Great article!"
    assert result.model == "claude-haiku-4-5-20251001"
    assert result.usage.input_tokens == 42
    assert result.usage.output_tokens == 7
    assert result.stop_reason == "end_turn"


async def test_complete_concatenates_multiple_text_blocks(
    mock_sdk: tuple[MagicMock, MagicMock],
) -> None:
    """complete() joins multiple text content blocks into a single string."""
    _, mock_instance = mock_sdk
    mock_instance.messages.create.return_value = _make_sdk_response(["Hello, ", "world!"])

    client = AnthropicClient(_make_settings())
    result = await client.complete([LLMMessage(role="user", content="hi")])

    assert result.text == "Hello, world!"


async def test_complete_uses_settings_defaults_when_no_overrides(
    mock_sdk: tuple[MagicMock, MagicMock],
) -> None:
    """complete() falls back to settings.llm_default_model and llm_max_tokens when caller passes None."""
    _, mock_instance = mock_sdk
    mock_instance.messages.create.return_value = _make_sdk_response(["ok"])

    settings = _make_settings(llm_default_model="my-default", llm_max_tokens=999)
    client = AnthropicClient(settings)
    await client.complete([LLMMessage(role="user", content="test")])

    call_kwargs = mock_instance.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "my-default"
    assert call_kwargs["max_tokens"] == 999


async def test_complete_uses_caller_overrides_over_defaults(
    mock_sdk: tuple[MagicMock, MagicMock],
) -> None:
    """complete() uses explicit model/max_tokens args instead of settings defaults."""
    _, mock_instance = mock_sdk
    mock_instance.messages.create.return_value = _make_sdk_response(["ok"])

    client = AnthropicClient(_make_settings(llm_default_model="default", llm_max_tokens=100))
    await client.complete(
        [LLMMessage(role="user", content="test")],
        model="override-model",
        max_tokens=50,
    )

    call_kwargs = mock_instance.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "override-model"
    assert call_kwargs["max_tokens"] == 50


async def test_complete_wraps_api_error_as_llm_error(
    mock_sdk: tuple[MagicMock, MagicMock],
) -> None:
    """complete() converts any anthropic.APIError into LLMError with __cause__ set."""
    _, mock_instance = mock_sdk
    original_error = anthropic.APIConnectionError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        message="network failure",
    )
    mock_instance.messages.create.side_effect = original_error

    client = AnthropicClient(_make_settings())

    with pytest.raises(LLMError) as exc_info:
        await client.complete([LLMMessage(role="user", content="fail")])

    assert exc_info.value.__cause__ is original_error
