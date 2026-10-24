from __future__ import annotations

from types import SimpleNamespace

import pytest

from lab_core.groq_client import GroqClientAdapter, LiveExecutionNotAllowed, normalize_usage


def test_live_execution_not_allowed_when_not_authorized():
    with pytest.raises(LiveExecutionNotAllowed):
        GroqClientAdapter(live_authorized=False, request_timeout_seconds=30.0)


def test_live_execution_not_allowed_without_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LiveExecutionNotAllowed):
        GroqClientAdapter(live_authorized=True, request_timeout_seconds=30.0)


def test_normalize_usage_none_input():
    usage = normalize_usage(None)
    assert usage.prompt_tokens is None
    assert usage.completion_tokens is None
    assert usage.cached_tokens is None
    assert usage.reasoning_tokens is None


def test_normalize_usage_missing_fields_stay_none():
    fake_usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    usage = normalize_usage(fake_usage)
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 20
    assert usage.total_tokens == 30
    assert usage.cached_tokens is None
    assert usage.reasoning_tokens is None


def test_normalize_usage_nested_fields_extracted_when_present():
    fake_usage = SimpleNamespace(
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        prompt_tokens_details=SimpleNamespace(cached_tokens=5),
        completion_tokens_details=SimpleNamespace(reasoning_tokens=7),
    )
    usage = normalize_usage(fake_usage)
    assert usage.cached_tokens == 5
    assert usage.reasoning_tokens == 7
