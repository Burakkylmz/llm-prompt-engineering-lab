"""Lab 05's evaluator: correct / near-miss-confused / explicit-not-found / hallucinated,
computed from the model's stated answer against the question's known candidate values
(gold and near-miss) — the same "compare against known candidates" pattern used by Labs 02
and 04, since the evaluator does not have direct access to the assembled context text.
"""

from __future__ import annotations

from lab_core.evaluation import EvaluationResult, normalize_text_tr
from lab_core.experiment_runner import Case


def evaluate_response(content: str, case: Case) -> EvaluationResult:
    gold_answer = case.expected["gold_answer"]
    near_miss_answer = case.expected["near_miss_answer"]
    normalized = normalize_text_tr(content)

    correct = normalize_text_tr(gold_answer) in normalized
    not_found = "bulunamadi" in normalized
    confused_by_near_miss = (not correct) and (normalize_text_tr(near_miss_answer) in normalized)
    hallucinated = (not correct) and (not not_found) and (not confused_by_near_miss)

    return EvaluationResult(
        checks={
            "exact_match": correct,
            "not_found_reported": not_found,
            "confused_by_near_miss": confused_by_near_miss,
            "hallucinated": hallucinated,
        },
        primary_correct=correct,
        parsed_label=None,
        notes={},
    )
