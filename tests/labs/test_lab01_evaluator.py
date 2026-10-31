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
        "within_length_bound": True,
        "all_constraints_met": True,
    }
    assert result.primary_correct is True


def test_trailing_explanation_after_contract_is_not_format_compliant():
    """Regression: the contract forbids any text outside the two lines. A `match` +
    re.MULTILINE regex previously accepted this response as compliant."""
    result = evaluate_response(
        "ETIKET: billing\nONCELIK: medium\nCunku musteri faturasindan bahsediyor.",
        _case("billing"),
    )
    assert result.primary_correct is True
    assert result.checks["format_compliant"] is False
    assert result.checks["all_constraints_met"] is False


def test_leading_text_before_contract_is_not_format_compliant():
    result = evaluate_response("Cevap:\nETIKET: billing\nONCELIK: medium", _case("billing"))
    assert result.checks["format_compliant"] is False


def test_length_bound_rejects_long_responses_even_with_valid_label():
    long_response = "ETIKET: billing " + "ek aciklama " * 10
    result = evaluate_response(long_response, _case("billing"))
    assert result.checks["within_length_bound"] is False
    assert result.checks["all_constraints_met"] is False


def test_all_constraints_met_is_conjunction_of_other_checks():
    result = evaluate_response("billing", _case("billing"))
    others = {k: v for k, v in result.checks.items() if k != "all_constraints_met"}
    assert result.checks["all_constraints_met"] == all(others.values())


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
