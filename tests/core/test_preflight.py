from __future__ import annotations

from lab_core.config import ModelPricing, PreflightConfig
from lab_core.preflight import build_preflight_plan, format_plan_report

CFG = PreflightConfig(
    max_requests_per_run=50,
    max_estimated_tokens_per_run=10_000,
    max_input_tokens_per_request=1_000,
    confirm_above_requests=10,
)


def test_plan_within_limits_does_not_abort_or_confirm():
    plan = build_preflight_plan(
        per_request_token_estimates=[100] * 5, preflight_config=CFG, pricing=None
    )
    assert plan.planned_requests == 5
    assert plan.estimated_total_tokens == 500
    assert plan.should_abort is False
    assert plan.requires_confirmation is False


def test_plan_exceeding_request_limit_aborts():
    plan = build_preflight_plan(
        per_request_token_estimates=[10] * 51, preflight_config=CFG, pricing=None
    )
    assert plan.exceeds_request_limit is True
    assert plan.should_abort is True


def test_plan_exceeding_token_limit_aborts():
    plan = build_preflight_plan(
        per_request_token_estimates=[5000, 6000], preflight_config=CFG, pricing=None
    )
    assert plan.exceeds_token_limit is True
    assert plan.should_abort is True


def test_plan_exceeding_per_request_limit_aborts():
    plan = build_preflight_plan(
        per_request_token_estimates=[1500], preflight_config=CFG, pricing=None
    )
    assert plan.exceeds_per_request_limit is True
    assert plan.should_abort is True


def test_plan_requires_confirmation_above_threshold_but_does_not_abort():
    plan = build_preflight_plan(
        per_request_token_estimates=[10] * 11, preflight_config=CFG, pricing=None
    )
    assert plan.requires_confirmation is True
    assert plan.should_abort is False


def test_plan_cost_is_none_without_verified_pricing():
    plan = build_preflight_plan(
        per_request_token_estimates=[100], preflight_config=CFG, pricing=None
    )
    assert plan.estimated_cost_usd is None


def test_plan_cost_computed_with_verified_pricing():
    pricing = ModelPricing(input_per_1m_usd=1.0, output_per_1m_usd=2.0)
    plan = build_preflight_plan(
        per_request_token_estimates=[1_000_000], preflight_config=CFG, pricing=pricing
    )
    assert plan.estimated_cost_usd == 1.0


def test_format_plan_report_mentions_abort_reasons():
    plan = build_preflight_plan(
        per_request_token_estimates=[10] * 51, preflight_config=CFG, pricing=None
    )
    report = format_plan_report(plan)
    assert "ABORT" in report
    assert "max_requests_per_run" in report


def test_format_plan_report_mentions_confirmation():
    plan = build_preflight_plan(
        per_request_token_estimates=[10] * 11, preflight_config=CFG, pricing=None
    )
    report = format_plan_report(plan)
    assert "CONFIRMATION REQUIRED" in report
