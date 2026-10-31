from __future__ import annotations

from labs.lab08_structured_outputs.data import MIN_RECORDS, load_records


def test_dataset_meets_minimum_size():
    cases, _payload = load_records()
    assert len(cases) >= MIN_RECORDS


def test_dataset_has_missing_fields_cases():
    cases, _payload = load_records()
    assert any(c.expected["amount"] is None for c in cases)


def test_dataset_has_multiple_candidates_and_normalization_tags():
    _cases, payload = load_records()
    tags = {tag for r in payload["records"] for tag in r["metadata"]["tags"]}
    assert "multiple_candidates" in tags
    assert "normalization_required" in tags


def test_dataset_covers_all_request_types():
    cases, _payload = load_records()
    types = {c.expected["request_type"] for c in cases}
    assert types == {"iade", "degisim", "bilgi_talebi", "sikayet", "iptal"}
