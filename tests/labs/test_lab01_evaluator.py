from __future__ import annotations

from lab_core.experiment_runner import Case
from labs.lab01_prompt_anatomy.evaluator import evaluate_response


def _case(label: str = "billing") -> Case:
    return Case(case_id="c1", input_text="x", expected={"label": label, "priority": "medium"})


def test_strict_format_all_checks_pass():
    result = evaluate_response("ETIKET: billing\nONCELIK: medium", _case("billing"))
    assert result.checks == {
        "label_in_closed_set": True,
        "priority_valid": True,
        "format_compliant": True,
    }
    assert result.primary_correct is True


def test_loose_text_with_correct_label_but_no_priority():
    result = evaluate_response("Bu mesaj sanirim billing ile ilgili olabilir.", _case("billing"))
    assert result.checks["label_in_closed_set"] is True
    assert result.checks["priority_valid"] is False
    assert result.checks["format_compliant"] is False
    assert result.primary_correct is True


def test_wrong_label_is_incorrect():
    result = evaluate_response("ETIKET: cancellation\nONCELIK: low", _case("billing"))
    assert result.primary_correct is False
    assert result.checks["label_in_closed_set"] is True  # a closed-set label was found
    assert result.checks["format_compliant"] is True  # format itself is still well-formed


def test_no_recognizable_label_is_incorrect_and_not_in_closed_set():
    result = evaluate_response("Üzgünüm, bu konuda yardımcı olamıyorum.", _case("billing"))
    assert result.checks["label_in_closed_set"] is False
    assert result.primary_correct is False
    assert result.parsed_label is None


def test_extra_text_around_strict_format_breaks_format_compliance():
    result = evaluate_response(
        "Tabii, iste cevabim:\nETIKET: billing\nONCELIK: medium", _case("billing")
    )
    assert result.checks["label_in_closed_set"] is True
    assert result.checks["format_compliant"] is False  # strict regex requires an exact match


def test_turkish_dotted_i_in_label_still_matches():
    # "İptal" is not one of our labels, but normalization robustness matters for any
    # Turkish free text surrounding the label token.
    result = evaluate_response("ETİKET bulunamadı ama billing olabilir", _case("billing"))
    assert result.checks["label_in_closed_set"] is True
