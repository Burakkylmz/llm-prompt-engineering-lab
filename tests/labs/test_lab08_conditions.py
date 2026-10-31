from __future__ import annotations

from labs.lab08_structured_outputs.conditions import CONDITION_ORDER, build_conditions


def test_condition_ids_match_spec_order():
    assert [c.condition_id for c in build_conditions()] == CONDITION_ORDER


def test_plain_nl_has_no_response_format():
    conditions = {c.condition_id: c for c in build_conditions()}
    assert conditions["plain_nl"].generation_overrides.get("response_format") is None


def test_json_schema_strict_sets_strict_true():
    conditions = {c.condition_id: c for c in build_conditions()}
    fmt = conditions["json_schema_strict"].generation_overrides["response_format"]
    assert fmt["json_schema"]["strict"] is True


def test_json_schema_best_effort_sets_strict_false():
    conditions = {c.condition_id: c for c in build_conditions()}
    fmt = conditions["json_schema_best_effort"].generation_overrides["response_format"]
    assert fmt["json_schema"]["strict"] is False


def test_json_object_mode_uses_json_object_type():
    conditions = {c.condition_id: c for c in build_conditions()}
    fmt = conditions["json_object_mode"].generation_overrides["response_format"]
    assert fmt == {"type": "json_object"}


def test_field_description_identical_across_json_conditions():
    conditions = {c.condition_id: c for c in build_conditions()}
    json_conditions = [
        "prompt_only_json",
        "json_object_mode",
        "json_schema_best_effort",
        "json_schema_strict",
    ]
    instructions = {conditions[cid].build_components().instruction for cid in json_conditions}
    assert len(instructions) == 1
