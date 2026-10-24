"""Per-condition orchestration: how many calls, in what order, with what's passed between
them. Bypasses `ExperimentRunner` deliberately (spec Section 11 LAB 07's multi-call
conditions do not fit the "one call per trial" shape every other lab uses) — see
`docs/decisions.md` for why. Every condition returns a `DecompositionResult` with whatever
intermediate fields it actually produced (`None` for fields a condition never computes,
e.g. `direct_answer` never extracts facts at all).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lab_core.groq_client import ChatClient, ChatMessage, CompletionRequest
from lab_core.metrics import UsageMetrics
from labs.lab07_task_decomposition.parsing import (
    parse_applicable_rules,
    parse_decision,
    parse_facts,
    parse_rule_outcomes,
)
from labs.lab07_task_decomposition.policy import rule_outcomes as compute_rule_outcomes

MAX_VALIDATOR_REASKS = 1


@dataclass
class DecompositionResult:
    final_decision: str | None
    extracted_facts: dict | None = None
    applicable_rules: list[str] | None = None
    rule_outcomes: dict | None = None
    api_call_count: int = 0
    total_usage: UsageMetrics = field(default_factory=UsageMetrics)
    total_latency_ms: float | None = None
    raw_responses: list[str] = field(default_factory=list)
    validator_triggered: bool = False


STEP_SEPARATOR = "\n---LAB07-STEP---\n"

SINGLE_CALL_CONDITIONS = {
    "direct_answer",
    "reasoning_low",
    "reasoning_medium",
    "reasoning_high",
}


def reconstruct_from_raw(condition_id: str, raw_responses: list[str]) -> DecompositionResult:
    """Re-derives a `DecompositionResult` from previously-recorded raw step responses, using
    the *current* parsers — this is what Lab 07's lightweight replay re-evaluates against
    (see `docs/decisions.md` for why Lab 07 does not reuse `lab_core.replay`'s generic
    prompt-hash drift detection: a multi-call trial has no single prompt to hash)."""
    if not raw_responses:
        return DecompositionResult(final_decision=None, raw_responses=raw_responses)

    if condition_id in SINGLE_CALL_CONDITIONS:
        content = raw_responses[0]
        return DecompositionResult(
            final_decision=parse_decision(content), api_call_count=1, raw_responses=raw_responses
        )

    if condition_id == "single_call_structured":
        content = raw_responses[0]
        return DecompositionResult(
            final_decision=parse_decision(content),
            extracted_facts=parse_facts(content),
            applicable_rules=parse_applicable_rules(content),
            rule_outcomes=parse_rule_outcomes(content),
            api_call_count=1,
            raw_responses=raw_responses,
        )

    if condition_id in ("multi_call_decomposition", "multi_call_validated"):
        # Call order is always: extract, determine-rules, evaluate[, re-ask evaluate], decide.
        # The decide call is always last; the evaluate call actually used is always
        # second-to-last, regardless of whether a re-ask happened (4 vs 5 total calls).
        facts = parse_facts(raw_responses[0]) if len(raw_responses) > 0 else None
        rules = parse_applicable_rules(raw_responses[1]) if len(raw_responses) > 1 else None
        outcomes = parse_rule_outcomes(raw_responses[-2]) if len(raw_responses) >= 2 else None
        decision = parse_decision(raw_responses[-1])
        return DecompositionResult(
            final_decision=decision,
            extracted_facts=facts,
            applicable_rules=rules,
            rule_outcomes=outcomes,
            api_call_count=len(raw_responses),
            raw_responses=raw_responses,
            validator_triggered=(
                condition_id == "multi_call_validated" and len(raw_responses) == 5
            ),
        )

    return DecompositionResult(final_decision=None, raw_responses=raw_responses)


def _sum_usage(a: UsageMetrics, b: UsageMetrics) -> UsageMetrics:
    def _add(x, y):
        if x is None and y is None:
            return None
        return (x or 0) + (y or 0)

    return UsageMetrics(
        prompt_tokens=_add(a.prompt_tokens, b.prompt_tokens),
        completion_tokens=_add(a.completion_tokens, b.completion_tokens),
        total_tokens=_add(a.total_tokens, b.total_tokens),
        cached_tokens=_add(a.cached_tokens, b.cached_tokens),
        reasoning_tokens=_add(a.reasoning_tokens, b.reasoning_tokens),
    )


def _call(client: ChatClient, model: str, system_text: str, user_text: str, params: dict):
    messages = (
        ChatMessage(role="system", content=system_text),
        ChatMessage(role="user", content=user_text),
    )
    request = CompletionRequest(
        messages=messages,
        model=model,
        temperature=params.get("temperature", 0.0),
        max_tokens=params.get("max_tokens"),
        reasoning_effort=params.get("reasoning_effort"),
        include_reasoning=params.get("include_reasoning", False),
    )
    return client.complete(request)


def run_direct_answer(client: ChatClient, case, model: str, params: dict) -> DecompositionResult:
    from labs.lab07_task_decomposition.prompts import DIRECT_SYSTEM

    result = _call(client, model, DIRECT_SYSTEM, case.input_text, params)
    return DecompositionResult(
        final_decision=parse_decision(result.content),
        api_call_count=1,
        total_usage=result.usage,
        total_latency_ms=result.performance.client_elapsed_ms,
        raw_responses=[result.content],
    )


def run_structured_single_call(
    client: ChatClient, case, model: str, params: dict
) -> DecompositionResult:
    from labs.lab07_task_decomposition.prompts import STRUCTURED_SINGLE_CALL_SYSTEM

    result = _call(client, model, STRUCTURED_SINGLE_CALL_SYSTEM, case.input_text, params)
    content = result.content
    return DecompositionResult(
        final_decision=parse_decision(content),
        extracted_facts=parse_facts(content),
        applicable_rules=parse_applicable_rules(content),
        rule_outcomes=parse_rule_outcomes(content),
        api_call_count=1,
        total_usage=result.usage,
        total_latency_ms=result.performance.client_elapsed_ms,
        raw_responses=[content],
    )


def _format_facts_for_prompt(facts: dict | None) -> str:
    if facts is None:
        return "(cikarilamadi)"
    return (
        f"TUTAR: {facts['amount']} | KATEGORI: {facts['category']} | "
        f"FIS: {'var' if facts['has_receipt'] else 'yok'} | "
        f"ONAY: {'var' if facts['manager_preapproved'] else 'yok'}"
    )


def run_multi_call_decomposition(
    client: ChatClient, case, model: str, params: dict, validate: bool = False
) -> DecompositionResult:
    from labs.lab07_task_decomposition.prompts import (
        DECIDE_SYSTEM,
        DETERMINE_RULES_SYSTEM,
        EVALUATE_RULES_SYSTEM,
        EXTRACT_FACTS_SYSTEM,
        REVALIDATE_RULES_SYSTEM,
    )

    raw_responses: list[str] = []
    total_usage = UsageMetrics()
    total_latency = 0.0
    api_calls = 0

    def _do(system_text: str, user_text: str):
        nonlocal total_usage, total_latency, api_calls
        result = _call(client, model, system_text, user_text, params)
        raw_responses.append(result.content)
        total_usage = _sum_usage(total_usage, result.usage)
        total_latency += result.performance.client_elapsed_ms or 0.0
        api_calls += 1
        return result.content

    # Step 1: extract facts.
    facts_content = _do(EXTRACT_FACTS_SYSTEM, case.input_text)
    extracted_facts = parse_facts(facts_content)

    # Step 2: determine applicable rules.
    facts_summary = _format_facts_for_prompt(extracted_facts)
    rules_content = _do(DETERMINE_RULES_SYSTEM, facts_summary)
    applicable_rules_list = parse_applicable_rules(rules_content)

    # Step 3: evaluate each applicable rule.
    rules_summary = f"{facts_summary} | GECERLI_KURALLAR: {', '.join(applicable_rules_list or [])}"
    outcomes_content = _do(EVALUATE_RULES_SYSTEM, rules_summary)
    outcomes = parse_rule_outcomes(outcomes_content)

    validator_triggered = False
    if validate and extracted_facts is not None:
        expected_outcomes = compute_rule_outcomes(
            amount=extracted_facts["amount"],
            category=extracted_facts["category"],
            has_receipt=extracted_facts["has_receipt"],
            manager_preapproved=extracted_facts["manager_preapproved"],
        )
        if outcomes != expected_outcomes:
            validator_triggered = True
            correction_note = (
                f"{rules_summary}\n\nUygulama dogrulamasi bu sonucu bekliyordu: "
                f"{expected_outcomes}. Lutfen bilgileri tekrar degerlendir."
            )
            outcomes_content = _do(REVALIDATE_RULES_SYSTEM, correction_note)
            outcomes = parse_rule_outcomes(outcomes_content)
            # Bounded: at most one re-ask (spec). If still inconsistent, the deterministic
            # validator's own computation is trusted over the model's for the final step —
            # this is what "application-side enforcement" means in practice.
            if outcomes != expected_outcomes:
                outcomes = expected_outcomes

    # Step 4: decide.
    outcomes_summary = (
        f"KURAL_SONUCLARI: {', '.join(f'{k}:{v}' for k, v in (outcomes or {}).items())}"
    )
    decision_content = _do(DECIDE_SYSTEM, outcomes_summary)
    decision = parse_decision(decision_content)

    return DecompositionResult(
        final_decision=decision,
        extracted_facts=extracted_facts,
        applicable_rules=applicable_rules_list,
        rule_outcomes=outcomes,
        api_call_count=api_calls,
        total_usage=total_usage,
        total_latency_ms=total_latency,
        raw_responses=raw_responses,
        validator_triggered=validator_triggered,
    )
