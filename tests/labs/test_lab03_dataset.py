from __future__ import annotations

from lab_core.datasets import edge_case_fraction
from labs.lab03_few_shot.data import (
    LABELS,
    MIN_EDGE_FRACTION,
    MIN_EVAL_CASES,
    MIN_PER_CLASS,
    MIN_POOL_CASES,
    PURPOSES,
    load_eval_and_pool,
)


def test_dataset_meets_minimum_sizes():
    eval_cases, pool_cases, eval_payload, pool_payload = load_eval_and_pool()
    assert len(eval_cases) >= MIN_EVAL_CASES
    assert len(pool_cases) >= MIN_POOL_CASES


def test_class_balance_meets_minimum():
    eval_cases, _pool, _e, _p = load_eval_and_pool()
    counts = {label: 0 for label in LABELS}
    for case in eval_cases:
        counts[case.expected["label"]] += 1
    for label, count in counts.items():
        assert count >= MIN_PER_CLASS, f"{label} has only {count}"


def test_edge_fraction_meets_minimum():
    _eval, _pool, eval_payload, _p = load_eval_and_pool()
    assert edge_case_fraction(eval_payload["cases"]) >= MIN_EDGE_FRACTION


def test_pool_covers_all_required_purposes():
    _eval, pool_cases, _e, _p = load_eval_and_pool()
    purposes_present = {c.metadata["purpose"] for c in pool_cases}
    assert set(PURPOSES) <= purposes_present


def test_eval_and_pool_are_disjoint():
    eval_cases, pool_cases, _e, _p = load_eval_and_pool()
    eval_ids = {c.case_id for c in eval_cases}
    pool_ids = {c.case_id for c in pool_cases}
    assert eval_ids.isdisjoint(pool_ids)
