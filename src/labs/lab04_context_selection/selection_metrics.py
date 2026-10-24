"""Selection-level metrics (spec Section 11 LAB 04: "no LLM needed"): evidence recall and
precision of the selector against gold evidence IDs, and the stale-document inclusion rate.
Computed directly from each condition's selector function against the question set — no
client, no prompt, no API call.
"""

from __future__ import annotations

from dataclasses import dataclass

from lab_core.context_manager import Document
from lab_core.experiment_runner import Case
from lab_core.statistics import ConfidenceInterval, wilson_ci


@dataclass(frozen=True)
class SelectionMetrics:
    evidence_recall: ConfidenceInterval
    evidence_precision: ConfidenceInterval
    stale_inclusion_rate: ConfidenceInterval
    n_questions: int


def compute_selection_metrics(
    cases: list[Case], select_fn, corpus_by_id: dict[str, Document]
) -> SelectionMetrics:
    recall_hits = 0
    precision_num = 0
    precision_denom = 0
    stale_included = 0

    for case in cases:
        gold_ids = set(case.expected["gold_evidence_doc_ids"])
        stale_doc_id = case.expected.get("stale_doc_id")

        selected_docs = select_fn(case.input_text)
        selected_ids = {doc.doc_id for doc in selected_docs}

        if gold_ids & selected_ids:
            recall_hits += 1
        if selected_ids:
            precision_num += len(selected_ids & gold_ids)
            precision_denom += len(selected_ids)
        if stale_doc_id and stale_doc_id in selected_ids:
            stale_included += 1

    n = len(cases)
    recall_ci = wilson_ci(recall_hits, n)
    # Precision is a per-document rate (TP / selected), not a per-question rate; Wilson CI
    # over the pooled counts is still a legitimate proportion CI, just at a different unit
    # of analysis than recall/stale-inclusion — documented here rather than silently implied
    # to be the same denominator.
    precision_ci = (
        wilson_ci(precision_num, precision_denom)
        if precision_denom > 0
        else ConfidenceInterval(point_estimate=0.0, low=0.0, high=0.0, n=0)
    )
    stale_ci = wilson_ci(stale_included, n)

    return SelectionMetrics(
        evidence_recall=recall_ci,
        evidence_precision=precision_ci,
        stale_inclusion_rate=stale_ci,
        n_questions=n,
    )
