"""Lab 06's evaluator: exact-match accuracy plus evidence identification (does the model
report the correct clause ID it used)."""

from __future__ import annotations

import re

from lab_core.evaluation import EvaluationResult, normalize_text_tr
from lab_core.experiment_runner import Case

_STRICT_RE = re.compile(r"^CEVAP:\s*(.+?)\s*\|\s*MADDE:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)


def evaluate_response(content: str, case: Case) -> EvaluationResult:
    gold_answer = case.expected["gold_answer"]
    near_miss_answer = case.expected["near_miss_answer"]
    gold_clause_id = case.metadata["clause_id"]

    normalized = normalize_text_tr(content)
    correct = normalize_text_tr(gold_answer) in normalized
    not_found = "bulunamadi" in normalized
    confused_by_near_miss = (not correct) and (normalize_text_tr(near_miss_answer) in normalized)

    match = _STRICT_RE.search(content.strip())
    cited_clause_id = match.group(2).strip() if match else None
    evidence_identified = (
        cited_clause_id is not None and cited_clause_id.upper() == gold_clause_id.upper()
    )

    return EvaluationResult(
        checks={
            "exact_match": correct,
            "not_found_reported": not_found,
            "confused_by_near_miss": confused_by_near_miss,
            "evidence_identified": evidence_identified,
        },
        primary_correct=correct,
        parsed_label=cited_clause_id,
        notes={"cited_clause_id": cited_clause_id},
    )
