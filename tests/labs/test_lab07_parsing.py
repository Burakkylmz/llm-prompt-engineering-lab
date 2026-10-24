from __future__ import annotations

from labs.lab07_task_decomposition.parsing import (
    parse_applicable_rules,
    parse_decision,
    parse_facts,
    parse_rule_outcomes,
)


def test_parse_facts_basic():
    facts = parse_facts("TUTAR: 2000 | KATEGORI: seyahat | FIS: var | ONAY: yok")
    assert facts == {
        "amount": 2000.0,
        "category": "seyahat",
        "has_receipt": True,
        "manager_preapproved": False,
    }


def test_parse_facts_handles_python_float_rendering():
    """Regression test: a round-tripped amount rendered as Python's str(float) (e.g.
    "800.0") must NOT be misread as Turkish thousands-separator notation (which would turn
    it into 8000.0). Found while testing the multi-call orchestration end to end."""
    facts = parse_facts("TUTAR: 800.0 | KATEGORI: seyahat | FIS: var | ONAY: var")
    assert facts["amount"] == 800.0


def test_parse_facts_handles_turkish_thousands_separator():
    facts = parse_facts("TUTAR: 1.500,50 | KATEGORI: egitim | FIS: yok | ONAY: yok")
    assert facts["amount"] == 1500.50


def test_parse_facts_missing_returns_none():
    assert parse_facts("hicbir bilgi yok") is None


def test_parse_applicable_rules():
    rules = parse_applicable_rules("GECERLI_KURALLAR: category_check,receipt_requirement")
    assert rules == ["category_check", "receipt_requirement"]


def test_parse_rule_outcomes():
    outcomes = parse_rule_outcomes("KURAL_SONUCLARI: category_check:pass,receipt_requirement:fail")
    assert outcomes == {"category_check": "pass", "receipt_requirement": "fail"}


def test_parse_decision():
    assert parse_decision("KARAR: approve") == "approve"
    assert parse_decision("baska bir metin") is None


def test_parse_facts_within_combined_single_call_response():
    content = (
        "TUTAR: 2000 | KATEGORI: seyahat | FIS: var | ONAY: yok | "
        "GECERLI_KURALLAR: category_check,receipt_requirement | "
        "KURAL_SONUCLARI: category_check:pass,receipt_requirement:pass | KARAR: approve"
    )
    assert parse_facts(content)["amount"] == 2000.0
    assert parse_applicable_rules(content) == ["category_check", "receipt_requirement"]
    assert parse_rule_outcomes(content) == {"category_check": "pass", "receipt_requirement": "pass"}
    assert parse_decision(content) == "approve"
