"""The trusted, deterministic expense-eligibility policy — used both to generate gold
dataset values and as the application-side validator in the `multi_call_validated`
condition (spec Section 11 LAB 07's "deterministic application-side validator")."""

from __future__ import annotations

ALLOWED_CATEGORIES = ["seyahat", "ofis_malzemesi", "egitim", "yazilim"]
RECEIPT_THRESHOLD = 1000
APPROVAL_THRESHOLD = 5000


def applicable_rules(amount: float, category: str) -> list[str]:
    rules = ["category_check"]
    if amount > RECEIPT_THRESHOLD:
        rules.append("receipt_requirement")
    if amount > APPROVAL_THRESHOLD:
        rules.append("approval_chain")
    return rules


def rule_outcomes(
    amount: float, category: str, has_receipt: bool, manager_preapproved: bool
) -> dict[str, str]:
    outcomes = {"category_check": "pass" if category in ALLOWED_CATEGORIES else "fail"}
    if amount > RECEIPT_THRESHOLD:
        outcomes["receipt_requirement"] = "pass" if has_receipt else "fail"
    if amount > APPROVAL_THRESHOLD:
        outcomes["approval_chain"] = "pass" if manager_preapproved else "fail"
    return outcomes


def decision_from_outcomes(outcomes: dict[str, str]) -> str:
    if outcomes.get("category_check") == "fail":
        return "deny"
    if outcomes.get("receipt_requirement") == "fail":
        return "escalate"
    if outcomes.get("approval_chain") == "fail":
        return "escalate"
    return "approve"


def final_decision(
    amount: float, category: str, has_receipt: bool, manager_preapproved: bool
) -> str:
    return decision_from_outcomes(rule_outcomes(amount, category, has_receipt, manager_preapproved))
