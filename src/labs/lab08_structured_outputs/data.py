"""Loads and validates Lab 08's dataset (spec Section 9.2: >=40 extraction records
including missing fields, ambiguous fields, multiple candidate values, values requiring
normalization)."""

from __future__ import annotations

from pathlib import Path

from lab_core.datasets import DatasetError, load_json, validate_against_schema
from lab_core.experiment_runner import Case

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "golden" / "lab08"
MIN_RECORDS = 40


def load_records() -> tuple[list[Case], dict]:
    payload = load_json(DATA_DIR / "records.json")
    validate_against_schema(payload, "lab08_records.schema.json")
    if len(payload["records"]) < MIN_RECORDS:
        raise DatasetError(f"Lab08 has {len(payload['records'])} records, minimum is {MIN_RECORDS}")

    cases = [
        Case(
            case_id=r["record_id"],
            input_text=r["text"],
            expected=r["gold"],
            metadata={"tags": r["metadata"]["tags"]},
        )
        for r in payload["records"]
    ]
    return cases, payload
