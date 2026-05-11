"""Smoke tests for the FakeLLMClient.

Verifies the test double satisfies the LLMClient protocol and behaves
as documented. Real provider clients get their own test files.
"""

from app.services.llm import LLMClient, LLMMessage
from app.services.llm.fakes import FakeLLMClient


def test_fake_client_satisfies_protocol() -> None:
    client: LLMClient = FakeLLMClient()
    assert isinstance(client, LLMClient)


async def test_fake_client_records_calls_and_returns_scripted_response() -> None:
    client = FakeLLMClient(responses=["first", "second"])

    r1 = await client.complete(
        [LLMMessage(role="user", content="hello")],
        system="be brief",
        model="test-model",
        max_tokens=100,
    )
    r2 = await client.complete([LLMMessage(role="user", content="again")])

    assert r1.text == "first"
    assert r2.text == "second"
    assert len(client.calls) == 2
    assert client.calls[0].system == "be brief"
    assert client.calls[0].model == "test-model"
    assert client.calls[1].system is None


async def test_fake_client_repeats_last_response_when_exhausted() -> None:
    client = FakeLLMClient(responses=["only"])

    r1 = await client.complete([LLMMessage(role="user", content="a")])
    r2 = await client.complete([LLMMessage(role="user", content="b")])

    assert r1.text == r2.text == "only"
