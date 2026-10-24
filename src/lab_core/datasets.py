"""Dataset loading, JSON-Schema validation, and the eval/example-pool leakage check
(spec Section 9.1). Powers both `lab-runner validate-data` and the test suite.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import jsonschema

from lab_core.text_similarity import shingle_jaccard

_REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = _REPO_ROOT / "data" / "schemas"


class DatasetError(ValueError):
    """Raised when a dataset file fails schema validation, class-balance checks, or the
    eval/example-pool leakage check."""


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(payload: dict[str, Any], schema_name: str) -> None:
    schema_path = SCHEMAS_DIR / schema_name
    schema = load_json(schema_path)
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except jsonschema.ValidationError as exc:
        raise DatasetError(
            f"{schema_name}: {exc.message} (path: {list(exc.absolute_path)})"
        ) from exc


def check_class_balance(cases: list[dict[str, Any]], labels: list[str], min_per_class: int) -> None:
    counts = {label: 0 for label in labels}
    for case in cases:
        if case["label"] not in counts:
            raise DatasetError(
                f"Case {case['case_id']!r} has label {case['label']!r} not in {labels}"
            )
        counts[case["label"]] += 1
    under = {label: n for label, n in counts.items() if n < min_per_class}
    if under:
        raise DatasetError(f"Classes under the minimum of {min_per_class} per class: {under}")


def check_leakage(
    eval_cases: list[dict[str, Any]],
    pool_cases: list[dict[str, Any]],
    threshold: float = 0.8,
) -> list[tuple[str, str, float]]:
    """Returns (eval_case_id, pool_case_id, similarity) for every eval/pool pair whose text
    similarity meets or exceeds `threshold` — i.e. the eval item leaks an example-pool item.
    An empty list means no leakage was found."""
    leaks: list[tuple[str, str, float]] = []
    for eval_case in eval_cases:
        for pool_case in pool_cases:
            similarity = shingle_jaccard(eval_case["text"], pool_case["text"])
            if similarity >= threshold:
                leaks.append((eval_case["case_id"], pool_case["case_id"], similarity))
    return leaks


def stratified_subset[T](items: list[T], max_count: int, key_fn: Callable[[T], str]) -> list[T]:
    """Round-robins across `key_fn` groups (in each group's original order) so a bounded
    subset stays class-balanced instead of being a prefix slice that can land entirely
    inside one class (spec Section 7: "the classroom profile uses a stratified subset").
    """
    if max_count >= len(items):
        return list(items)
    if max_count <= 0:
        return []

    groups: dict[str, list[T]] = {}
    for item in items:
        groups.setdefault(key_fn(item), []).append(item)

    group_iters = {key: iter(values) for key, values in groups.items()}
    result: list[T] = []
    keys = list(groups.keys())
    while len(result) < max_count and group_iters:
        for key in list(keys):
            if len(result) >= max_count:
                break
            iterator = group_iters.get(key)
            if iterator is None:
                continue
            try:
                result.append(next(iterator))
            except StopIteration:
                del group_iters[key]
    return result


def edge_case_fraction(cases: list[dict[str, Any]]) -> float:
    if not cases:
        return 0.0
    edge_tags = {"edge_case", "ambiguous"}
    flagged = sum(1 for c in cases if edge_tags & set(c["metadata"]["tags"]))
    return flagged / len(cases)
