from __future__ import annotations

from lab_core.config import ModelPricing
from lab_core.metrics import UsageMetrics, estimate_cost


def test_cost_none_when_no_pricing():
    usage = UsageMetrics(prompt_tokens=100, completion_tokens=50)
    result = estimate_cost(usage, None)
    assert result.estimated_cost_usd is None
    assert "no pricing" in result.reason


def test_cost_none_when_pricing_unverified():
    usage = UsageMetrics(prompt_tokens=100, completion_tokens=50)
    pricing = ModelPricing(input_per_1m_usd=None, output_per_1m_usd=None)
    result = estimate_cost(usage, pricing)
    assert result.estimated_cost_usd is None


def test_cost_none_when_usage_not_reported():
    usage = UsageMetrics(prompt_tokens=None, completion_tokens=None)
    pricing = ModelPricing(input_per_1m_usd=0.075, output_per_1m_usd=0.30)
    result = estimate_cost(usage, pricing)
    assert result.estimated_cost_usd is None
    assert "did not report" in result.reason


def test_cost_computed_when_both_present():
    usage = UsageMetrics(prompt_tokens=1_000_000, completion_tokens=1_000_000)
    pricing = ModelPricing(input_per_1m_usd=0.075, output_per_1m_usd=0.30)
    result = estimate_cost(usage, pricing)
    assert result.estimated_cost_usd == 0.075 + 0.30
    assert result.reason is None


def test_cost_none_when_cached_reported_but_price_unverified():
    usage = UsageMetrics(prompt_tokens=1000, completion_tokens=100, cached_tokens=500)
    pricing = ModelPricing(
        input_per_1m_usd=0.075, output_per_1m_usd=0.30, cached_input_per_1m_usd=None
    )
    result = estimate_cost(usage, pricing)
    assert result.estimated_cost_usd is None
    assert "cached" in result.reason


def test_cost_accounts_for_cached_tokens_when_price_known():
    usage = UsageMetrics(prompt_tokens=1_000_000, completion_tokens=0, cached_tokens=1_000_000)
    pricing = ModelPricing(
        input_per_1m_usd=0.075, output_per_1m_usd=0.30, cached_input_per_1m_usd=0.0375
    )
    result = estimate_cost(usage, pricing)
    # All prompt tokens are cached: billable prompt tokens = 0, cached cost = 0.0375.
    assert result.estimated_cost_usd == 0.0375
