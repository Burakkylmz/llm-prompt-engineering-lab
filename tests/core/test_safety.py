"""Spec Section 13/14 safety requirements: no code path can reach the network in
fixture/replay mode, and live execution requires both gates."""

from __future__ import annotations

import pytest

from lab_core.groq_client import GroqClientAdapter, LiveExecutionNotAllowed


@pytest.mark.parametrize("live_authorized", [False])
def test_adapter_refuses_construction_when_not_authorized(live_authorized: bool):
    with pytest.raises(LiveExecutionNotAllowed):
        GroqClientAdapter(live_authorized=live_authorized, request_timeout_seconds=10.0)


def test_adapter_refuses_even_with_api_key_if_not_authorized(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-should-not-matter")
    with pytest.raises(LiveExecutionNotAllowed):
        GroqClientAdapter(live_authorized=False, request_timeout_seconds=10.0)
