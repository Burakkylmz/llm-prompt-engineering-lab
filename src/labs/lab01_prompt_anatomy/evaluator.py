"""Lab 01's deterministic evaluator.

Three independently-reportable checks are applied to *every* condition's raw response,
regardless of whether that condition's prompt actually asked for them — this is the point:
baseline/A/B conditions were never told to produce the strict two-line format, so they are
expected to score low on `format_compliant` and `priority_valid` even when the label itself
(found via a lenient search) is correct. Only C/D, which add the explicit output contract,
are expected to score high on all three.
"""

from __future__ import annotations

import re

from lab_core.evaluation import EvaluationResult, closed_set_match, normalize_text_tr
from lab_core.experiment_runner import Case
from labs.lab01_prompt_anatomy.data import LABELS, PRIORITIES

_STRICT_FORMAT_RE = re.compile(
    r"^ETIKET:\s*(\S+)\s*\n\s*ONCELIK:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE
)


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

    match = _STRICT_FORMAT_RE.match(content.strip())
    format_compliant = False
    if match:
        raw_label, raw_priority = match.group(1).strip(), match.group(2).strip()
        format_compliant = any(closed_set_match(raw_label, label) for label in LABELS) and any(
            closed_set_match(raw_priority, p) for p in PRIORITIES
        )

    primary_correct = label_in_closed_set and closed_set_match(parsed_label, gold_label)

    return EvaluationResult(
        checks={
            "label_in_closed_set": label_in_closed_set,
            "priority_valid": priority_valid,
            "format_compliant": format_compliant,
        },
        primary_correct=primary_correct,
        parsed_label=parsed_label,
        notes={"parsed_priority": parsed_priority},
    )
