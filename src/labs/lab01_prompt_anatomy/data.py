"""Loads and validates Lab 01's dataset (spec Section 9.2: eval >=60, 5 classes, >=12/class,
>=15% edge/ambiguous; example pool >=15, leakage-checked against eval)."""

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

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "golden" / "lab01"

LABELS = ["billing", "technical_issue", "cancellation", "complaint", "general_inquiry"]
PRIORITIES = ["low", "medium", "high"]

MIN_EVAL_CASES = 60
MIN_PER_CLASS = 12
MIN_EDGE_FRACTION = 0.15
MIN_POOL_CASES = 15
LEAKAGE_THRESHOLD = 0.8


def _to_cases(payload: dict) -> list[Case]:
    return [
        Case(
            case_id=c["case_id"],
            input_text=c["text"],
            expected={"label": c["label"], "priority": c["priority"]},
            metadata=c["metadata"],
        )
        for c in payload["cases"]
    ]


def load_eval_and_pool() -> tuple[list[Case], list[Case], dict, dict]:
    """Loads, schema-validates, and sanity-checks the eval/pool datasets. Raises
    DatasetError if any spec Section 9.2 minimum is not met. Returns
    (eval_cases, pool_cases, eval_payload, pool_payload)."""
    eval_payload = load_json(DATA_DIR / "eval.json")
    pool_payload = load_json(DATA_DIR / "example_pool.json")

    validate_against_schema(eval_payload, "lab01_case_set.schema.json")
    validate_against_schema(pool_payload, "lab01_case_set.schema.json")

    if len(eval_payload["cases"]) < MIN_EVAL_CASES:
        raise DatasetError(
            f"Lab01 eval set has {len(eval_payload['cases'])} cases, minimum is {MIN_EVAL_CASES}"
        )
    if len(pool_payload["cases"]) < MIN_POOL_CASES:
        raise DatasetError(
            f"Lab01 example pool has {len(pool_payload['cases'])} cases, "
            f"minimum is {MIN_POOL_CASES}"
        )

    check_class_balance(eval_payload["cases"], labels=LABELS, min_per_class=MIN_PER_CLASS)

    edge_fraction = edge_case_fraction(eval_payload["cases"])
    if edge_fraction < MIN_EDGE_FRACTION:
        raise DatasetError(
            f"Lab01 eval set edge/ambiguous fraction is {edge_fraction:.1%}, "
            f"minimum is {MIN_EDGE_FRACTION:.0%}"
        )

    leaks = check_leakage(eval_payload["cases"], pool_payload["cases"], threshold=LEAKAGE_THRESHOLD)
    if leaks:
        raise DatasetError(f"Leakage detected between eval and example_pool: {leaks}")

    return _to_cases(eval_payload), _to_cases(pool_payload), eval_payload, pool_payload
