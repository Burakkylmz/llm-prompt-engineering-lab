from __future__ import annotations

from lab_core.experiment_runner import Case
from labs.lab06_lost_in_middle.evaluator import evaluate_response


def _case():
    return Case(
        case_id="c1",
        input_text="q",
        expected={"gold_answer": "750000 TL", "near_miss_answer": "500000 TL"},
        metadata={"clause_id": "MADDE-07"},
    )


def test_correct_answer_and_evidence_identified():
    result = evaluate_response("CEVAP: 750000 TL | MADDE: MADDE-07", _case())
    assert result.primary_correct is True
    assert result.checks["evidence_identified"] is True


def test_correct_answer_but_wrong_clause_cited():
    result = evaluate_response("CEVAP: 750000 TL | MADDE: MADDE-02", _case())
    assert result.primary_correct is True
    assert result.checks["evidence_identified"] is False


def test_confused_by_near_miss():
    result = evaluate_response("CEVAP: 500000 TL | MADDE: MADDE-07", _case())
    assert result.checks["confused_by_near_miss"] is True
    assert result.primary_correct is False


def test_not_found():
    result = evaluate_response("CEVAP: BULUNAMADI | MADDE: YOK", _case())
    assert result.checks["not_found_reported"] is True
    assert result.checks["evidence_identified"] is False
