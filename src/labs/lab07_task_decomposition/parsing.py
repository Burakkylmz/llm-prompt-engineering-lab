"""Shared output parsers for every step's response format, used by both the orchestration
(to feed one step's output into the next) and the evaluator (to score against gold)."""

from __future__ import annotations

import re

_FACTS_RE = re.compile(
    r"TUTAR:\s*([\d.,]+)\s*\|\s*KATEGORI:\s*(\S+)\s*\|\s*FIS:\s*(var|yok)\s*\|\s*ONAY:\s*(var|yok)",
    re.IGNORECASE,
)
_RULES_RE = re.compile(r"GECERLI_KURALLAR:\s*([^\n|]+)", re.IGNORECASE)
_OUTCOMES_RE = re.compile(r"KURAL_SONUCLARI:\s*([^\n]+?)(?:\s*\||\s*$)", re.IGNORECASE)
_DECISION_RE = re.compile(r"KARAR:\s*(approve|deny|escalate)", re.IGNORECASE)


def _parse_amount(amount_str: str) -> float | None:
    """Accepts both Turkish/European-style numbers ('.' thousands separator, ','
    decimal separator, e.g. "1.500,50") and plain style ('.' decimal point, no thousands
    separator, e.g. "800.0" — what Python's own `str(float)` produces, which matters
    because an extracted amount gets re-rendered and re-parsed between orchestration
    steps). Disambiguated by the presence of a comma: only Turkish-style numbers use one.
    """
    amount_str = amount_str.strip()
    normalized = amount_str.replace(".", "").replace(",", ".") if "," in amount_str else amount_str
    try:
        return float(normalized)
    except ValueError:
        return None


def parse_facts(content: str) -> dict | None:
    match = _FACTS_RE.search(content)
    if not match:
        return None
    amount_str, category, fis, onay = match.groups()
    amount = _parse_amount(amount_str)
    if amount is None:
        return None
    return {
        "amount": amount,
        "category": category.strip().strip(",").lower(),
        "has_receipt": fis.lower() == "var",
        "manager_preapproved": onay.lower() == "var",
    }


def parse_applicable_rules(content: str) -> list[str] | None:
    match = _RULES_RE.search(content)
    if not match:
        return None
    return [r.strip().lower() for r in match.group(1).split(",") if r.strip()]


def parse_rule_outcomes(content: str) -> dict[str, str] | None:
    match = _OUTCOMES_RE.search(content)
    if not match:
        return None
    outcomes: dict[str, str] = {}
    for pair in match.group(1).split(","):
        if ":" not in pair:
            continue
        rule_id, status = pair.split(":", 1)
        outcomes[rule_id.strip().lower()] = status.strip().lower()
    return outcomes or None


def parse_decision(content: str) -> str | None:
    match = _DECISION_RE.search(content)
    return match.group(1).lower() if match else None
