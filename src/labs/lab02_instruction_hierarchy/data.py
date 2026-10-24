"""Loads and validates Lab 02's dataset (spec Section 9.2: >=30 refund cases with gold
decisions; >=20 injection fixtures covering >=5 injection types; >=10 benign controls)."""

from __future__ import annotations

from pathlib import Path

from lab_core.datasets import DatasetError, load_json, validate_against_schema
from lab_core.experiment_runner import Case

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "golden" / "lab02"

DECISIONS = ["approve", "deny", "escalate"]
MIN_CLEAN_CASES = 30
MIN_INJECTION_CASES = 20
MIN_INJECTION_TYPES = 5
MIN_BENIGN_CASES = 10


def _to_case(raw: dict) -> Case:
    return Case(
        case_id=raw["case_id"],
        input_text=raw["customer_text"],
        expected={
            "gold_decision": raw["gold_decision"],
            "hard_violation": raw["hard_violation"],
            "attack_goal": raw["attack_goal"],
        },
        metadata={
            "case_type": raw["case_type"],
            "untrusted": raw["untrusted"],
            "trusted": raw["trusted"],
            "tags": raw["metadata"]["tags"],
        },
    )


def load_cases() -> tuple[list[Case], list[Case], list[Case], dict]:
    """Returns (clean_cases, injection_cases, benign_control_cases, raw_payload)."""
    payload = load_json(DATA_DIR / "eval.json")
    validate_against_schema(payload, "lab02_case_set.schema.json")

    clean = [c for c in payload["cases"] if c["case_type"] == "clean"]
    injection = [c for c in payload["cases"] if c["case_type"] == "injection"]
    benign = [c for c in payload["cases"] if c["case_type"] == "benign_control"]

    if len(clean) < MIN_CLEAN_CASES:
        raise DatasetError(
            f"Lab02 has {len(clean)} clean decision cases, minimum is {MIN_CLEAN_CASES}"
        )
    if len(injection) < MIN_INJECTION_CASES:
        raise DatasetError(
            f"Lab02 has {len(injection)} injection cases, minimum is {MIN_INJECTION_CASES}"
        )
    injection_types = {c["untrusted"]["injection_type"] for c in injection}
    if len(injection_types) < MIN_INJECTION_TYPES:
        raise DatasetError(
            f"Lab02 injection cases cover {len(injection_types)} types, "
            f"minimum is {MIN_INJECTION_TYPES}"
        )
    if len(benign) < MIN_BENIGN_CASES:
        raise DatasetError(
            f"Lab02 has {len(benign)} benign controls, minimum is {MIN_BENIGN_CASES}"
        )

    return (
        [_to_case(c) for c in clean],
        [_to_case(c) for c in injection],
        [_to_case(c) for c in benign],
        payload,
    )
