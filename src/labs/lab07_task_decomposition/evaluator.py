"""Scores a `DecompositionResult` against a case's gold fields. Only includes a check key
for an intermediate value the condition actually produced (e.g. `direct_answer` never adds
`facts_correct`), consistent with Lab 02's "only add a check when it's meaningful" pattern.
"""

from __future__ import annotations

from lab_core.evaluation import EvaluationResult
from labs.lab07_task_decomposition.orchestration import DecompositionResult


def evaluate_result(result: DecompositionResult, case) -> EvaluationResult:
    gold = case.expected
    decision_correct = result.final_decision == gold["gold_decision"]

    checks: dict[str, bool] = {"decision_correct": decision_correct}

    if result.extracted_facts is not None:
        checks["facts_correct"] = result.extracted_facts == gold["gold_facts"]
    if result.applicable_rules is not None:
        checks["applicable_rules_correct"] = set(result.applicable_rules) == set(
            gold["gold_applicable_rules"]
        )
    if result.rule_outcomes is not None:
        checks["rule_outcomes_correct"] = result.rule_outcomes == gold["gold_rule_outcomes"]

    return EvaluationResult(
        checks=checks,
        primary_correct=decision_correct,
        parsed_label=result.final_decision,
        notes={
            "api_call_count": result.api_call_count,
            "validator_triggered": result.validator_triggered,
        },
    )
