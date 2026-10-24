"""Pre-flight plan for live runs (spec Section 7): before any API call, compute and print
the planned request count, estimated tokens, largest single request, and estimated cost;
abort if configured limits are exceeded, and require explicit confirmation above a lower
threshold. This runs purely on local *estimates* (never provider-reported usage, which does
not exist yet at plan time) and is always labeled as such.
"""

from __future__ import annotations

from dataclasses import dataclass

from lab_core.config import ModelPricing, PreflightConfig


@dataclass(frozen=True)
class PreflightPlan:
    planned_requests: int
    estimated_total_tokens: int
    largest_single_request_tokens: int
    estimated_cost_usd: float | None
    exceeds_request_limit: bool
    exceeds_token_limit: bool
    exceeds_per_request_limit: bool
    requires_confirmation: bool

    @property
    def should_abort(self) -> bool:
        return (
            self.exceeds_request_limit or self.exceeds_token_limit or self.exceeds_per_request_limit
        )


def build_preflight_plan(
    *,
    per_request_token_estimates: list[int],
    preflight_config: PreflightConfig,
    pricing: ModelPricing | None,
) -> PreflightPlan:
    planned_requests = len(per_request_token_estimates)
    estimated_total_tokens = sum(per_request_token_estimates)
    largest = max(per_request_token_estimates) if per_request_token_estimates else 0

    estimated_cost_usd = None
    if pricing is not None and pricing.input_per_1m_usd is not None:
        # Planning-time estimate only: assumes every estimated token is an input token,
        # since output length is unknown before the call. Always a conservative upper-bound
        # style estimate for the purpose of aborting an oversized run, never presented as a
        # measured cost (measured cost only ever comes from lab_core.metrics.estimate_cost
        # using provider-reported usage after the call).
        estimated_cost_usd = (estimated_total_tokens / 1_000_000) * pricing.input_per_1m_usd

    return PreflightPlan(
        planned_requests=planned_requests,
        estimated_total_tokens=estimated_total_tokens,
        largest_single_request_tokens=largest,
        estimated_cost_usd=estimated_cost_usd,
        exceeds_request_limit=planned_requests > preflight_config.max_requests_per_run,
        exceeds_token_limit=estimated_total_tokens > preflight_config.max_estimated_tokens_per_run,
        exceeds_per_request_limit=largest > preflight_config.max_input_tokens_per_request,
        requires_confirmation=planned_requests > preflight_config.confirm_above_requests,
    )


def format_plan_report(plan: PreflightPlan) -> str:
    lines = [
        "[pre-flight plan] (estimates, not measured)",
        f"  planned requests: {plan.planned_requests}",
        f"  estimated total input tokens: {plan.estimated_total_tokens}",
        f"  largest single request (estimated tokens): {plan.largest_single_request_tokens}",
        "  estimated cost (USD): "
        + (
            f"{plan.estimated_cost_usd:.4f}"
            if plan.estimated_cost_usd is not None
            else "unknown (pricing unverified)"
        ),
    ]
    if plan.exceeds_request_limit:
        lines.append("  ABORT: planned requests exceed preflight.max_requests_per_run")
    if plan.exceeds_token_limit:
        lines.append(
            "  ABORT: estimated total tokens exceed preflight.max_estimated_tokens_per_run"
        )
    if plan.exceeds_per_request_limit:
        lines.append("  ABORT: largest request exceeds preflight.max_input_tokens_per_request")
    if plan.requires_confirmation and not plan.should_abort:
        lines.append(
            "  CONFIRMATION REQUIRED: pass --yes to proceed "
            "(above preflight.confirm_above_requests)"
        )
    return "\n".join(lines)
