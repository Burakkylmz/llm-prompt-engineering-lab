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

    # Intermediate-step checks apply to every condition whose contract includes intermediate
    # values; a value that could not be parsed is wrong (False), not "not applicable".
    if result.intermediates_expected:
        checks["facts_correct"] = (
            result.extracted_facts is not None and result.extracted_facts == gold["gold_facts"]
        )
        checks["applicable_rules_correct"] = result.applicable_rules is not None and set(
            result.applicable_rules
        ) == set(gold["gold_applicable_rules"])
        checks["rule_outcomes_correct"] = (
            result.rule_outcomes is not None and result.rule_outcomes == gold["gold_rule_outcomes"]
        )

    return EvaluationResult(
        checks=checks,
        primary_correct=decision_correct,
        parsed_label=result.final_decision,
        notes={
            "api_call_count": result.api_call_count,
            "validator_triggered": result.validator_triggered,
        },
    )
