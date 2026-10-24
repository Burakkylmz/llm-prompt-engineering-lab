"""Shared measurement schema.

Any field the Groq API does not report for a given call (e.g. reasoning_tokens on a response
that doesn't include one, or cached_tokens when nothing was cached) MUST stay `None`, never
defaulted to 0. `None` means "unavailable/not reported" — a different fact from "reported as
zero" — and every consumer of these dataclasses (statistics, reporting) must preserve that
distinction (spec Section 7/8).
"""

from __future__ import annotations

from dataclasses import dataclass

from lab_core.config import ModelPricing


@dataclass(frozen=True)
class UsageMetrics:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass(frozen=True)
class PerformanceMetrics:
    client_elapsed_ms: float | None = None
    provider_elapsed_ms: float | None = None


@dataclass(frozen=True)
class CostEstimate:
    estimated_cost_usd: float | None
    reason: str | None = None
    """Set (and estimated_cost_usd=None) when pricing is missing/unverified for this model."""


def estimate_cost(usage: UsageMetrics, pricing: ModelPricing | None) -> CostEstimate:
    """Compute cost from *reported* usage and verified pricing only.

    Returns CostEstimate(None, reason=...) rather than fabricating a 0 or partial figure
    whenever pricing or usage is missing or unverified, per spec Section 10 ("missing values
    stay missing: null plus a reason, never 0").
    """
    if pricing is None:
        return CostEstimate(None, reason="no pricing entry configured for this model")
    if pricing.input_per_1m_usd is None or pricing.output_per_1m_usd is None:
        return CostEstimate(None, reason="input/output pricing not verified for this model")
    if usage.prompt_tokens is None or usage.completion_tokens is None:
        return CostEstimate(None, reason="provider did not report prompt/completion tokens")

    billable_prompt_tokens = usage.prompt_tokens
    cached_cost = 0.0
    if usage.cached_tokens is not None and usage.cached_tokens > 0:
        if pricing.cached_input_per_1m_usd is None:
            return CostEstimate(
                None, reason="cached tokens were reported but cached-input price is unverified"
            )
        billable_prompt_tokens = usage.prompt_tokens - usage.cached_tokens
        cached_cost = (usage.cached_tokens / 1_000_000) * pricing.cached_input_per_1m_usd

    prompt_cost = (billable_prompt_tokens / 1_000_000) * pricing.input_per_1m_usd
    completion_cost = (usage.completion_tokens / 1_000_000) * pricing.output_per_1m_usd
    return CostEstimate(prompt_cost + completion_cost + cached_cost)
