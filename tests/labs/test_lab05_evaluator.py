from __future__ import annotations

from lab_core.experiment_runner import Case
from labs.lab05_context_rot.evaluator import evaluate_response


def _case():
    return Case(
        case_id="c1",
        input_text="q",
        expected={"gold_answer": "750000 TL", "near_miss_answer": "500000 TL"},
    )


def test_correct_answer():
    result = evaluate_response("CEVAP: 750000 TL", _case())
    assert result.primary_correct is True
    assert result.checks["exact_match"] is True
    assert result.checks["hallucinated"] is False


def test_confused_by_near_miss():
    result = evaluate_response("CEVAP: 500000 TL", _case())
    assert result.primary_correct is False
    assert result.checks["confused_by_near_miss"] is True
    assert result.checks["hallucinated"] is False


def test_not_found_reported():
    result = evaluate_response("CEVAP: BULUNAMADI", _case())
    assert result.checks["not_found_reported"] is True
    assert result.checks["hallucinated"] is False
    assert result.primary_correct is False


def test_hallucinated_answer():
    result = evaluate_response("CEVAP: 999999 TL", _case())
    assert result.checks["hallucinated"] is True
    assert result.checks["confused_by_near_miss"] is False
    assert result.checks["not_found_reported"] is False
