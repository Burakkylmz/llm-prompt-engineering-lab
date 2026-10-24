from __future__ import annotations

from lab_core.experiment_runner import Case
from labs.lab03_few_shot.evaluator import evaluate_response


def _case(label="hot", edge=False):
    return Case(
        case_id="c1",
        input_text="x",
        expected={"label": label},
        metadata={"tags": ["edge_case"] if edge else []},
    )


def test_correct_label_detected():
    result = evaluate_response("ETIKET: hot", _case("hot"))
    assert result.primary_correct is True
    assert result.checks["label_in_closed_set"] is True


def test_wrong_label_detected():
    result = evaluate_response("ETIKET: cold", _case("hot"))
    assert result.primary_correct is False


def test_no_label_found():
    result = evaluate_response("Bilmiyorum.", _case("hot"))
    assert result.checks["label_in_closed_set"] is False
    assert result.primary_correct is False


def test_edge_case_correctness_tracked_only_for_edge_cases():
    result = evaluate_response("ETIKET: hot", _case("hot", edge=True))
    assert result.checks["edge_case_correct"] is True

    result2 = evaluate_response("ETIKET: hot", _case("hot", edge=False))
    assert "edge_case_correct" not in result2.checks
