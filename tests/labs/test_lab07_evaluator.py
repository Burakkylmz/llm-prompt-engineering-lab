from __future__ import annotations

from lab_core.experiment_runner import Case
from labs.lab07_task_decomposition.evaluator import evaluate_result
from labs.lab07_task_decomposition.orchestration import DecompositionResult


def _case():
    return Case(
        case_id="c1",
        input_text="x",
        expected={
            "gold_facts": {
                "amount": 2000,
                "category": "seyahat",
                "has_receipt": True,
                "manager_preapproved": False,
            },
            "gold_applicable_rules": ["category_check", "receipt_requirement"],
            "gold_rule_outcomes": {"category_check": "pass", "receipt_requirement": "pass"},
            "gold_decision": "approve",
        },
    )


def test_direct_answer_only_checks_decision():
    result = DecompositionResult(final_decision="approve", api_call_count=1)
    ev = evaluate_result(result, _case())
    assert ev.checks == {"decision_correct": True}


def test_structured_checks_all_intermediate_fields():
    case = _case()
    result = DecompositionResult(
        final_decision="approve",
        extracted_facts=case.expected["gold_facts"],
        applicable_rules=case.expected["gold_applicable_rules"],
        rule_outcomes=case.expected["gold_rule_outcomes"],
        api_call_count=1,
    )
    ev = evaluate_result(result, case)
    assert all(ev.checks.values())


def test_wrong_facts_detected():
    case = _case()
    result = DecompositionResult(
        final_decision="approve",
        extracted_facts={
            "amount": 999,
            "category": "seyahat",
            "has_receipt": True,
            "manager_preapproved": False,
        },
    )
    ev = evaluate_result(result, case)
    assert ev.checks["facts_correct"] is False


def test_notes_carry_api_call_count_and_validator_flag():
    result = DecompositionResult(
        final_decision="approve", api_call_count=5, validator_triggered=True
    )
    ev = evaluate_result(result, _case())
    assert ev.notes["api_call_count"] == 5
    assert ev.notes["validator_triggered"] is True
