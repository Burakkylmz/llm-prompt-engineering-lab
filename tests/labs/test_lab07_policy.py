from __future__ import annotations

from labs.lab07_task_decomposition.policy import (
    applicable_rules,
    decision_from_outcomes,
    final_decision,
    rule_outcomes,
)


def test_category_check_fails_denies_regardless_of_amount():
    assert final_decision(500, "eglence", True, True) == "deny"


def test_small_amount_clean_category_approves():
    assert final_decision(500, "seyahat", False, False) == "approve"


def test_receipt_required_above_threshold():
    assert "receipt_requirement" in applicable_rules(2000, "seyahat")
    assert final_decision(2000, "seyahat", False, False) == "escalate"
    assert final_decision(2000, "seyahat", True, False) == "approve"


def test_approval_chain_required_above_threshold():
    assert "approval_chain" in applicable_rules(6000, "seyahat")
    assert final_decision(6000, "seyahat", True, False) == "escalate"
    assert final_decision(6000, "seyahat", True, True) == "approve"


def test_applicable_rules_excludes_thresholds_not_crossed():
    assert applicable_rules(500, "seyahat") == ["category_check"]


def test_decision_from_outcomes_matches_final_decision():
    outcomes = rule_outcomes(6000, "seyahat", True, False)
    assert decision_from_outcomes(outcomes) == final_decision(6000, "seyahat", True, False)
