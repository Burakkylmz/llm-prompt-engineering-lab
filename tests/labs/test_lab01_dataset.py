from __future__ import annotations

from labs.lab01_prompt_anatomy.data import (
    LABELS,
    MIN_EDGE_FRACTION,
    MIN_EVAL_CASES,
    MIN_PER_CLASS,
    MIN_POOL_CASES,
    load_eval_and_pool,
)


def test_dataset_loads_and_validates_against_schema():
    eval_cases, pool_cases, eval_payload, pool_payload = load_eval_and_pool()
    assert len(eval_cases) >= MIN_EVAL_CASES
    assert len(pool_cases) >= MIN_POOL_CASES
    assert eval_payload["labels"] == LABELS
    assert pool_payload["labels"] == LABELS


def test_dataset_class_balance_meets_minimum():
    eval_cases, _pool_cases, _e, _p = load_eval_and_pool()
    counts = {label: 0 for label in LABELS}
    for case in eval_cases:
        counts[case.expected["label"]] += 1
    for label, count in counts.items():
        assert count >= MIN_PER_CLASS, f"{label} has only {count} cases"


def test_dataset_edge_case_fraction_meets_minimum():
    eval_cases, _pool_cases, eval_payload, _p = load_eval_and_pool()
    from lab_core.datasets import edge_case_fraction

    fraction = edge_case_fraction(eval_payload["cases"])
    assert fraction >= MIN_EDGE_FRACTION


def test_dataset_eval_and_pool_are_disjoint_ids():
    eval_cases, pool_cases, _e, _p = load_eval_and_pool()
    eval_ids = {c.case_id for c in eval_cases}
    pool_ids = {c.case_id for c in pool_cases}
    assert eval_ids.isdisjoint(pool_ids)


def test_dataset_every_case_has_valid_priority():
    eval_cases, pool_cases, _e, _p = load_eval_and_pool()
    for case in eval_cases + pool_cases:
        assert case.expected["priority"] in ("low", "medium", "high")
