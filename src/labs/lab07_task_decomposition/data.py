"""Loads and validates Lab 07's dataset (spec Section 9.2: >=30 eligibility cases with
gold final decisions AND gold intermediate values)."""

from __future__ import annotations

from pathlib import Path

from lab_core.datasets import DatasetError, load_json, validate_against_schema
from lab_core.experiment_runner import Case

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "golden" / "lab07"
MIN_CASES = 30


def load_cases() -> tuple[list[Case], dict]:
    payload = load_json(DATA_DIR / "cases.json")
    validate_against_schema(payload, "lab07_cases.schema.json")
    if len(payload["cases"]) < MIN_CASES:
        raise DatasetError(f"Lab07 has {len(payload['cases'])} cases, minimum is {MIN_CASES}")

    cases = [
        Case(
            case_id=c["case_id"],
            input_text=c["description"],
            expected={
                "gold_facts": c["gold_facts"],
                "gold_applicable_rules": c["gold_applicable_rules"],
                "gold_rule_outcomes": c["gold_rule_outcomes"],
                "gold_decision": c["gold_decision"],
            },
        )
        for c in payload["cases"]
    ]
    return cases, payload
