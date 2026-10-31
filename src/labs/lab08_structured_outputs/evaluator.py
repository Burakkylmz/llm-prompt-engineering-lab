"""Lab 08's three-layer evaluator (spec Section 11 LAB 08): JSON parse success, schema
adherence (always checked, even under strict mode — strict mode guarantees this layer at
most, never semantic correctness), and per-field semantic accuracy."""

from __future__ import annotations

import json

import jsonschema

from lab_core.evaluation import EvaluationResult, normalize_text_tr
from lab_core.experiment_runner import Case
from labs.lab08_structured_outputs.schema import EXTRACTION_SCHEMA

_TOP_LEVEL_FIELDS = [
    "customer_reference",
    "request_type",
    "amount",
    "currency",
    "product",
    "urgency",
]


def _lenient_json_parse(content: str) -> dict | None:
    """Tries a direct parse first (what a well-behaved JSON-mode response looks like), then
    falls back to extracting the outermost {...} substring (what a free-text response with
    JSON embedded in prose looks like) — this leniency is what lets `plain_nl` and
    `prompt_only_json` be scored by the same evaluator as the JSON-mode conditions, making
    the "gap" between them visible (spec: "evaluated by a lenient parser to show the gap")."""
    try:
        parsed = json.loads(content.strip())
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        pass

    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(content[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _values_equal(actual: object, gold: object) -> bool:
    if actual is None and gold is None:
        return True
    if actual is None or gold is None:
        return False
    if isinstance(gold, int | float) and isinstance(actual, int | float):
        return abs(float(actual) - float(gold)) < 0.01
    if isinstance(gold, str) and isinstance(actual, str):
        return normalize_text_tr(actual) == normalize_text_tr(gold)
    return actual == gold


def evaluate_response(content: str, case: Case) -> EvaluationResult:
    gold = case.expected
    parsed = _lenient_json_parse(content)
    parse_success = parsed is not None

    schema_adherent = False
    if parsed is not None:
        try:
            jsonschema.validate(instance=parsed, schema=EXTRACTION_SCHEMA)
            schema_adherent = True
        except jsonschema.ValidationError:
            schema_adherent = False

    field_correct: dict[str, bool] = {}
    if parsed is not None:
        for field in _TOP_LEVEL_FIELDS:
            field_correct[field] = _values_equal(parsed.get(field), gold.get(field))
        contact = parsed.get("contact_info")
        contact = contact if isinstance(contact, dict) else {}
        field_correct["contact_email"] = _values_equal(
            contact.get("email"), gold["contact_info"]["email"]
        )
        field_correct["contact_phone"] = _values_equal(
            contact.get("phone"), gold["contact_info"]["phone"]
        )

    semantic_correct = parse_success and bool(field_correct) and all(field_correct.values())

    return EvaluationResult(
        checks={
            "json_parse_success": parse_success,
            "schema_adherent": schema_adherent,
            "semantic_correct": semantic_correct,
        },
        primary_correct=semantic_correct,
        parsed_label=None,
        notes={"field_correct": field_correct},
    )
