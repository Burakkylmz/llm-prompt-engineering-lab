from __future__ import annotations

from lab_core.experiment_runner import Case
from labs.lab04_context_selection.evaluator import evaluate_response


def _case(gold_answer="20 gun", gold_doc="cur-1", stale_value="14 gun", stale_doc="old-1"):
    return Case(
        case_id="c1",
        input_text="soru",
        expected={
            "gold_answer": gold_answer,
            "gold_evidence_doc_ids": [gold_doc],
            "stale_value": stale_value,
            "stale_doc_id": stale_doc,
        },
    )


def test_correct_grounded_answer_with_correct_citation():
    result = evaluate_response("CEVAP: 20 gun | KAYNAK: cur-1", _case())
    assert result.checks["grounded_answer_correct"] is True
    assert result.checks["citation_correct"] is True
    assert result.primary_correct is True


def test_correct_answer_with_wrong_citation():
    result = evaluate_response("CEVAP: 20 gun | KAYNAK: unrelated-doc", _case())
    assert result.checks["grounded_answer_correct"] is True
    assert result.checks["citation_correct"] is False


def test_stale_answer_detected():
    result = evaluate_response("CEVAP: 14 gun | KAYNAK: old-1", _case())
    assert result.checks["stale_answer"] is True
    assert result.checks["grounded_answer_correct"] is False


def test_not_found_reported():
    result = evaluate_response("CEVAP: bulunamadi | KAYNAK: yok", _case())
    assert result.checks["not_found_reported"] is True
    assert result.checks["grounded_answer_correct"] is False
    assert result.checks["stale_answer"] is False


def test_completely_wrong_answer():
    result = evaluate_response("CEVAP: 99 gun | KAYNAK: yok", _case())
    assert result.checks["grounded_answer_correct"] is False
    assert result.checks["stale_answer"] is False
