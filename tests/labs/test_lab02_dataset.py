from __future__ import annotations

from labs.lab02_instruction_hierarchy.data import (
    MIN_BENIGN_CASES,
    MIN_CLEAN_CASES,
    MIN_INJECTION_CASES,
    MIN_INJECTION_TYPES,
    load_cases,
)


def test_dataset_meets_minimum_sizes():
    clean, injection, benign, _payload = load_cases()
    assert len(clean) >= MIN_CLEAN_CASES
    assert len(injection) >= MIN_INJECTION_CASES
    assert len(benign) >= MIN_BENIGN_CASES


def test_injection_cases_cover_minimum_types():
    _clean, injection, _benign, _payload = load_cases()
    types = {c.metadata["untrusted"]["injection_type"] for c in injection}
    assert len(types) >= MIN_INJECTION_TYPES


def test_every_case_has_valid_gold_decision():
    clean, injection, benign, _payload = load_cases()
    for case in clean + injection + benign:
        assert case.expected["gold_decision"] in ("approve", "deny", "escalate")


def test_hard_violation_cases_have_gold_deny():
    """A hard_violation case (not defective, >30 days) must never have a gold decision of
    approve — this is exactly the invariant condition C's enforcer relies on."""
    clean, injection, benign, _payload = load_cases()
    for case in clean + injection + benign:
        if case.expected["hard_violation"]:
            assert case.expected["gold_decision"] == "deny"


def test_benign_controls_have_no_attack_goal():
    _clean, _injection, benign, _payload = load_cases()
    for case in benign:
        assert case.expected["attack_goal"] is None


def test_injection_cases_have_an_attack_goal():
    _clean, injection, _benign, _payload = load_cases()
    for case in injection:
        assert case.expected["attack_goal"] in ("force_approve", "leak_canary")
