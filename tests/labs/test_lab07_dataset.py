from __future__ import annotations

from labs.lab07_task_decomposition.data import MIN_CASES, load_cases
from labs.lab07_task_decomposition.policy import final_decision


def test_dataset_meets_minimum_size():
    cases, _payload = load_cases()
    assert len(cases) >= MIN_CASES


def test_every_case_gold_decision_matches_policy_recomputation():
    """The dataset's gold_decision must be reproducible from gold_facts via the same
    deterministic policy function the validator uses — otherwise the "gold" values
    would not actually be internally consistent."""
    cases, _payload = load_cases()
    for case in cases:
        facts = case.expected["gold_facts"]
        recomputed = final_decision(
            facts["amount"], facts["category"], facts["has_receipt"], facts["manager_preapproved"]
        )
        assert recomputed == case.expected["gold_decision"], case.case_id


def test_dataset_covers_all_three_decisions():
    cases, _payload = load_cases()
    decisions = {c.expected["gold_decision"] for c in cases}
    assert decisions == {"approve", "deny", "escalate"}
