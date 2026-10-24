"""Loads and validates Lab 03's dataset (spec Section 9.2: eval >=80, 5 classes, >=15/class,
>=20% edge cases; example pool >=30, each tagged typical/boundary/redundant/
misleading_candidate)."""

from __future__ import annotations

from pathlib import Path

from lab_core.datasets import (
    DatasetError,
    check_class_balance,
    check_leakage,
    edge_case_fraction,
    load_json,
    validate_against_schema,
)
from lab_core.experiment_runner import Case

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "golden" / "lab03"

LABELS = ["hot", "warm", "cold", "not_a_lead", "partner_inquiry"]
PURPOSES = ["typical", "boundary", "redundant", "misleading_candidate"]

MIN_EVAL_CASES = 80
MIN_PER_CLASS = 15
MIN_EDGE_FRACTION = 0.20
MIN_POOL_CASES = 30
LEAKAGE_THRESHOLD = 0.8


def _to_eval_case(raw: dict) -> Case:
    return Case(
        case_id=raw["case_id"],
        input_text=raw["text"],
        expected={"label": raw["label"]},
        metadata=raw["metadata"],
    )


def _to_pool_case(raw: dict) -> Case:
    return Case(
        case_id=raw["case_id"],
        input_text=raw["text"],
        expected={"label": raw["label"]},
        metadata={**raw["metadata"], "purpose": raw["purpose"]},
    )


def load_eval_and_pool() -> tuple[list[Case], list[Case], dict, dict]:
    eval_payload = load_json(DATA_DIR / "eval.json")
    pool_payload = load_json(DATA_DIR / "example_pool.json")

    validate_against_schema(eval_payload, "lab03_eval.schema.json")
    validate_against_schema(pool_payload, "lab03_example_pool.schema.json")

    if len(eval_payload["cases"]) < MIN_EVAL_CASES:
        raise DatasetError(
            f"Lab03 eval set has {len(eval_payload['cases'])} cases, minimum is {MIN_EVAL_CASES}"
        )
    if len(pool_payload["cases"]) < MIN_POOL_CASES:
        raise DatasetError(
            f"Lab03 example pool has {len(pool_payload['cases'])} cases, "
            f"minimum is {MIN_POOL_CASES}"
        )

    check_class_balance(eval_payload["cases"], labels=LABELS, min_per_class=MIN_PER_CLASS)

    edge_fraction = edge_case_fraction(eval_payload["cases"])
    if edge_fraction < MIN_EDGE_FRACTION:
        raise DatasetError(
            f"Lab03 eval set edge fraction is {edge_fraction:.1%}, "
            f"minimum is {MIN_EDGE_FRACTION:.0%}"
        )

    purposes_present = {c["purpose"] for c in pool_payload["cases"]}
    missing = set(PURPOSES) - purposes_present
    if missing:
        raise DatasetError(f"Lab03 example pool is missing purposes: {missing}")

    leaks = check_leakage(eval_payload["cases"], pool_payload["cases"], threshold=LEAKAGE_THRESHOLD)
    if leaks:
        raise DatasetError(f"Leakage detected between eval and example_pool: {leaks}")

    return (
        [_to_eval_case(c) for c in eval_payload["cases"]],
        [_to_pool_case(c) for c in pool_payload["cases"]],
        eval_payload,
        pool_payload,
    )
