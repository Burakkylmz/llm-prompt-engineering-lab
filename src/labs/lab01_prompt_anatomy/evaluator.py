"""Lab 01's deterministic evaluator.

Four independently-reportable instruction-adherence checks, plus their conjunction, are
applied to *every* condition's raw response, regardless of whether that condition's prompt
actually asked for them — this is the point: baseline/A/B conditions were never told to
produce the strict two-line format, so they are expected to score low on `format_compliant`
and `priority_valid` even when the label itself (found via a lenient search) is correct.
Only C/D, which add the explicit output contract, are expected to score high on all of them.

Checks (spec Section 11, LAB 01 "instruction adherence"):
- `label_in_closed_set`: a label from the closed set appears in the response (lenient).
- `priority_valid`: a priority value from the closed set appears (lenient).
- `format_compliant`: the *entire* response is exactly the two-line contract — no text
  before or after it ("no text outside the contract").
- `within_length_bound`: the stripped response is at most `MAX_RESPONSE_CHARS` characters.
- `all_constraints_met`: all four of the above.
"""

from __future__ import annotations

import re

from lab_core.evaluation import EvaluationResult, closed_set_match, normalize_text_tr
from lab_core.experiment_runner import Case
from labs.lab01_prompt_anatomy.data import LABELS, PRIORITIES

# Used with `fullmatch`, so nothing may precede or follow the two contract lines. (An earlier
# `match` + re.MULTILINE version accepted trailing explanation text as compliant.)
_STRICT_FORMAT_RE = re.compile(
    r"ETIKET:[ \t]*(\S+)[ \t]*\n[ \t]*ONCELIK:[ \t]*(\S+)", re.IGNORECASE
)

# The longest valid contract response ("ETIKET: technical_issue\nONCELIK: medium") is 39
# characters; 60 leaves room for whitespace variations while still rejecting any added
# sentence.
MAX_RESPONSE_CHARS = 60


def _find_first(haystack_normalized: str, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if normalize_text_tr(candidate) in haystack_normalized:
            return candidate
    return None


def evaluate_response(content: str, case: Case) -> EvaluationResult:
    gold_label = case.expected["label"]
    normalized = normalize_text_tr(content)

    parsed_label = _find_first(normalized, LABELS)
    parsed_priority = _find_first(normalized, PRIORITIES)

    label_in_closed_set = parsed_label is not None
    priority_valid = parsed_priority is not None

    stripped = content.strip()
    match = _STRICT_FORMAT_RE.fullmatch(stripped)
    format_compliant = False
    if match:
        raw_label, raw_priority = match.group(1).strip(), match.group(2).strip()
        format_compliant = any(closed_set_match(raw_label, label) for label in LABELS) and any(
            closed_set_match(raw_priority, p) for p in PRIORITIES
        )

    within_length_bound = len(stripped) <= MAX_RESPONSE_CHARS

    primary_correct = label_in_closed_set and closed_set_match(parsed_label, gold_label)

    checks = {
        "label_in_closed_set": label_in_closed_set,
        "priority_valid": priority_valid,
        "format_compliant": format_compliant,
        "within_length_bound": within_length_bound,
    }
    checks["all_constraints_met"] = all(checks.values())

    return EvaluationResult(
        checks=checks,
        primary_correct=primary_correct,
        parsed_label=parsed_label,
        notes={"parsed_priority": parsed_priority},
    )
