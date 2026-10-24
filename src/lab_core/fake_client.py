"""Deterministic fake client used in fixture mode.

`FakeGroqClient` makes no network call and needs no API key. It resolves each request's
content via an injected `resolver` callable, so each lab can supply either a fixture-file
lookup or a deterministic rule (spec Section 5) without this module knowing about labs,
conditions, or cases at all — that composition happens in `src/labs/*/fixtures.py` (M2).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lab_core.config import TokensConfig
from lab_core.groq_client import CompletionRequest, CompletionResult
from lab_core.metrics import PerformanceMetrics, UsageMetrics
from lab_core.tokens import estimate_messages_tokens, estimate_tokens

Resolver = Callable[[CompletionRequest], str]


def _default_usage(
    request: CompletionRequest, content: str, tokens_config: TokensConfig
) -> UsageMetrics:
    """Fixture-mode usage is itself estimated (never claimed as provider-reported); reports
    generated from fixture-mode runs are watermarked SIMULATED and must not be read as real
    token measurements."""
    prompt_tokens = estimate_messages_tokens([m.as_dict() for m in request.messages], tokens_config)
    completion_tokens = estimate_tokens(content, tokens_config)
    return UsageMetrics(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cached_tokens=None,
        reasoning_tokens=None,
    )


@dataclass
class FakeGroqClient:
    resolver: Resolver
    tokens_config: TokensConfig

    def __post_init__(self) -> None:
        self.calls: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.calls.append(request)
        content = self.resolver(request)
        usage = _default_usage(request, content, self.tokens_config)
        return CompletionResult(
            content=content,
            usage=usage,
            performance=PerformanceMetrics(client_elapsed_ms=0.0, provider_elapsed_ms=None),
            model=request.model,
            raw=None,
        )


def canned_sequence_resolver(responses: list[str]) -> Resolver:
    """Simplest possible resolver: returns each queued response in order.

    Useful for core unit tests that don't need per-case fixture logic.
    """
    queue = list(responses)

    def _resolve(_request: CompletionRequest) -> str:
        if not queue:
            raise AssertionError("FakeGroqClient resolver ran out of canned responses")
        return queue.pop(0)

    return _resolve
