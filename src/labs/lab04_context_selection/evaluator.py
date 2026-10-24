"""Lab 04's answer-level evaluator: grounded answer accuracy, citation correctness, and
stale-answer detection — computed from the model's response and the question's gold fields
alone (no dependency on which documents were actually selected; that's the selection-level
metrics in `selection_metrics.py`, computed separately with no LLM call at all)."""

from __future__ import annotations

import re

from lab_core.evaluation import EvaluationResult, normalize_text_tr
from lab_core.experiment_runner import Case

_STRICT_RE = re.compile(r"^CEVAP:\s*(.+?)\s*\|\s*KAYNAK:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)


def evaluate_response(content: str, case: Case) -> EvaluationResult:
    gold_answer = case.expected["gold_answer"]
    gold_evidence = set(case.expected["gold_evidence_doc_ids"])
    stale_value = case.expected.get("stale_value")

    normalized_content = normalize_text_tr(content)
    answer_correct = normalize_text_tr(gold_answer) in normalized_content

    match = _STRICT_RE.search(content.strip())
    cited_doc_id = match.group(2).strip() if match else None
    citation_correct = cited_doc_id is not None and cited_doc_id in gold_evidence

    is_stale = (
        not answer_correct
        and stale_value is not None
        and normalize_text_tr(stale_value) in normalized_content
    )
    not_found = "bulunamadi" in normalized_content

    return EvaluationResult(
        checks={
            "grounded_answer_correct": answer_correct,
            "citation_correct": citation_correct,
            "stale_answer": is_stale,
            "not_found_reported": not_found,
        },
        primary_correct=answer_correct,
        parsed_label=cited_doc_id,
        notes={"cited_doc_id": cited_doc_id},
    )
