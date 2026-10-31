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
        intermediates_expected=True,
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
        intermediates_expected=True,
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


def test_unparseable_intermediates_count_as_wrong_not_absent():
    """Regression: when a structured/multi-call condition's intermediate output could not be
    parsed (None), the check must be False. Omitting it would make it "not applicable",
    and with per-check denominators that would inflate intermediate-step accuracy."""
    result = DecompositionResult(
        final_decision="approve",
        extracted_facts=None,
        applicable_rules=None,
        rule_outcomes=None,
        intermediates_expected=True,
    )
    ev = evaluate_result(result, _case())
    assert ev.checks["facts_correct"] is False
    assert ev.checks["applicable_rules_correct"] is False
    assert ev.checks["rule_outcomes_correct"] is False


def test_reconstructed_results_flag_intermediates_by_condition():
    from labs.lab07_task_decomposition.orchestration import reconstruct_from_raw

    assert reconstruct_from_raw("direct_answer", ["KARAR: approve"]).intermediates_expected is False
    assert (
        reconstruct_from_raw("reasoning_high", ["KARAR: approve"]).intermediates_expected is False
    )
    assert reconstruct_from_raw("single_call_structured", ["x"]).intermediates_expected is True
    assert (
        reconstruct_from_raw(
            "multi_call_decomposition", ["a", "b", "c", "d"]
        ).intermediates_expected
        is True
    )
