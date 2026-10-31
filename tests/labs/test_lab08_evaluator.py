from __future__ import annotations

import json

from lab_core.experiment_runner import Case
from labs.lab08_structured_outputs.evaluator import evaluate_response


def _case():
    return Case(
        case_id="c1",
        input_text="x",
        expected={
            "customer_reference": "KE-2001",
            "request_type": "iade",
            "amount": 500,
            "currency": "TL",
            "product": "akilli saat",
            "urgency": "orta",
            "contact_info": {"email": "a@b.com", "phone": None},
        },
    )


def test_valid_json_all_correct():
    case = _case()
    result = evaluate_response(json.dumps(case.expected, ensure_ascii=False), case)
    assert result.checks == {
        "json_parse_success": True,
        "schema_adherent": True,
        "semantic_correct": True,
    }
    assert result.primary_correct is True


def test_free_text_fails_all_three_layers():
    result = evaluate_response("Musterinin talebi bir iade talebidir.", _case())
    assert result.checks["json_parse_success"] is False
    assert result.checks["schema_adherent"] is False
    assert result.checks["semantic_correct"] is False


def test_json_embedded_in_prose_is_leniently_parsed():
    case = _case()
    content = f"Iste cevabim: {json.dumps(case.expected, ensure_ascii=False)} Tesekkurler."
    result = evaluate_response(content, case)
    assert result.checks["json_parse_success"] is True
    assert result.checks["semantic_correct"] is True


def test_valid_json_but_wrong_field_value():
    case = _case()
    wrong = dict(case.expected)
    wrong["amount"] = 9999
    result = evaluate_response(json.dumps(wrong, ensure_ascii=False), case)
    assert result.checks["json_parse_success"] is True
    assert result.checks["schema_adherent"] is True
    assert result.checks["semantic_correct"] is False
    assert result.notes["field_correct"]["amount"] is False


def test_schema_violation_missing_required_key():
    case = _case()
    broken = dict(case.expected)
    del broken["urgency"]
    result = evaluate_response(json.dumps(broken, ensure_ascii=False), case)
    assert result.checks["json_parse_success"] is True
    assert result.checks["schema_adherent"] is False


def test_null_fields_match_when_both_null():
    case = _case()  # phone is None in gold
    result = evaluate_response(json.dumps(case.expected, ensure_ascii=False), case)
    assert result.notes["field_correct"]["contact_phone"] is True
