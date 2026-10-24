from __future__ import annotations

import pytest

from lab_core.config import TokensConfig
from lab_core.fake_client import FakeGroqClient, canned_sequence_resolver
from lab_core.groq_client import ChatMessage, CompletionRequest

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def _request(content: str = "merhaba") -> CompletionRequest:
    return CompletionRequest(
        messages=(ChatMessage(role="user", content=content),),
        model="openai/gpt-oss-20b",
    )


def test_fake_client_returns_resolver_output_and_never_touches_network():
    client = FakeGroqClient(resolver=lambda _req: "billing", tokens_config=TOKENS_CFG)
    result = client.complete(_request())
    assert result.content == "billing"
    assert result.model == "openai/gpt-oss-20b"
    assert result.usage.prompt_tokens is not None  # estimated, not provider-reported
    assert len(client.calls) == 1


def test_fake_client_records_calls_in_order():
    client = FakeGroqClient(resolver=canned_sequence_resolver(["a", "b"]), tokens_config=TOKENS_CFG)
    first = client.complete(_request("one"))
    second = client.complete(_request("two"))
    assert (first.content, second.content) == ("a", "b")
    assert len(client.calls) == 2


def test_canned_sequence_resolver_raises_when_exhausted():
    client = FakeGroqClient(resolver=canned_sequence_resolver(["only"]), tokens_config=TOKENS_CFG)
    client.complete(_request())
    with pytest.raises(AssertionError):
        client.complete(_request())
