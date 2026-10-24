"""The real Groq client adapter, plus the shared request/result shapes and client Protocol
that `fake_client.py` and `replay.py` also implement.

Safety (spec Section 13): `GroqClientAdapter.__init__` raises `LiveExecutionNotAllowed` unless
explicitly told it is authorized. The caller (CLI layer) computes authorization from
`config.execution.live_api_enabled AND --live`, so this class can never be constructed with a
working connection by accident — this is the second of two layers (the CLI-level gate is the
first); together they satisfy "no code path can reach the network in fixture or replay mode"
without relying on either layer alone.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

from lab_core.metrics import PerformanceMetrics, UsageMetrics


class LiveExecutionNotAllowed(RuntimeError):
    """Raised when live execution was requested but is not authorized, or a key is missing."""


class UnsupportedCapabilityError(RuntimeError):
    """A request parameter (e.g. a response_format mode, reasoning_effort value) is not
    supported by the selected model. Callers must record this as a *skip*, not a failure
    (spec Section 7/8)."""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class CompletionRequest:
    messages: tuple[ChatMessage, ...]
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None
    reasoning_effort: str | None = None
    include_reasoning: bool = False
    response_format: dict[str, Any] | None = None


@dataclass(frozen=True)
class CompletionResult:
    content: str
    usage: UsageMetrics
    performance: PerformanceMetrics
    model: str
    retries: int = 0
    raw: Any = None


class ChatClient(Protocol):
    """Shared interface implemented by GroqClientAdapter, FakeGroqClient, and the replay reader."""

    def complete(self, request: CompletionRequest) -> CompletionResult: ...


def _get_nested(obj: Any, *path: str) -> Any | None:
    current = obj
    for attr in path:
        if current is None:
            return None
        current = getattr(current, attr, None)
    return current


def normalize_usage(usage: Any) -> UsageMetrics:
    """Convert the SDK's `usage` object into UsageMetrics, defaulting every missing field to
    None (never 0) — see module docstring in metrics.py for why this distinction matters."""
    if usage is None:
        return UsageMetrics()
    return UsageMetrics(
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
        cached_tokens=_get_nested(usage, "prompt_tokens_details", "cached_tokens"),
        reasoning_tokens=_get_nested(usage, "completion_tokens_details", "reasoning_tokens"),
    )


def normalize_server_timing(usage: Any) -> float | None:
    total_time = getattr(usage, "total_time", None) if usage is not None else None
    return total_time * 1000 if total_time is not None else None


class GroqClientAdapter:
    """Thin, single-purpose wrapper around the official `groq` SDK.

    Responsibilities, and only these: construct the SDK client (guarded by authorization),
    time each call client-side, normalize usage/timing defensively, classify
    unsupported-parameter errors distinctly from retryable/fatal ones. Retry *policy* (attempt
    count, backoff) is applied by the caller using `lab_core.rate_limiter`, not hidden here.
    """

    def __init__(self, *, live_authorized: bool, request_timeout_seconds: float) -> None:
        if not live_authorized:
            raise LiveExecutionNotAllowed(
                "GroqClientAdapter requires live_authorized=True. This is only true when "
                "both execution.live_api_enabled=true (config) and --live (CLI) were given."
            )
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise LiveExecutionNotAllowed(
                "Live execution is authorized but GROQ_API_KEY is not set in the environment."
            )
        # Imported lazily so fixture/replay runs never need the package installed to matter.
        from groq import Groq

        self._client = Groq(api_key=api_key, timeout=request_timeout_seconds)

    def complete(self, request: CompletionRequest) -> CompletionResult:
        import groq as groq_sdk

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": [m.as_dict() for m in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.reasoning_effort is not None:
            kwargs["reasoning_effort"] = request.reasoning_effort
        kwargs["include_reasoning"] = request.include_reasoning
        if request.response_format is not None:
            kwargs["response_format"] = request.response_format

        start = time.perf_counter()
        try:
            response = self._client.chat.completions.create(**kwargs, stream=False)
        except groq_sdk.BadRequestError as exc:
            message = str(exc).lower()
            if "unsupported" in message or "not supported" in message:
                raise UnsupportedCapabilityError(str(exc)) from exc
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000

        usage = getattr(response, "usage", None)
        content = response.choices[0].message.content if response.choices else ""
        return CompletionResult(
            content=content or "",
            usage=normalize_usage(usage),
            performance=PerformanceMetrics(
                client_elapsed_ms=elapsed_ms,
                provider_elapsed_ms=normalize_server_timing(usage),
            ),
            model=request.model,
            raw=response,
        )
