"""Lab 03's evaluator: closed-set label match via a lenient search, plus an
`edge_case`-aware check surfaced for the edge-case-accuracy metric the spec calls for."""

from __future__ import annotations

from lab_core.evaluation import EvaluationResult, normalize_text_tr
from lab_core.experiment_runner import Case
from labs.lab03_few_shot.data import LABELS


def _find_label(normalized: str) -> str | None:
    for label in LABELS:
        if normalize_text_tr(label) in normalized:
            return label
    return None


def evaluate_response(content: str, case: Case) -> EvaluationResult:
    gold = case.expected["label"]
    normalized = normalize_text_tr(content)
    parsed_label = _find_label(normalized)

    label_in_closed_set = parsed_label is not None
    correct = label_in_closed_set and parsed_label == gold
    is_edge_case = "edge_case" in case.metadata.get("tags", [])

    checks = {
        "label_in_closed_set": label_in_closed_set,
    }
    if is_edge_case:
        checks["edge_case_correct"] = correct

    return EvaluationResult(
        checks=checks,
        primary_correct=correct,
        parsed_label=parsed_label,
        notes={"is_edge_case": is_edge_case},
    )
