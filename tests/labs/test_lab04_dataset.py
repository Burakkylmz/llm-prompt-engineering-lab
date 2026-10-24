from __future__ import annotations

from labs.lab04_context_selection.data import (
    MIN_CORPUS_DOCS,
    MIN_QUESTIONS,
    MIN_SUPERSEDED_PAIRS,
    load_corpus,
    load_questions,
)


def test_corpus_meets_minimum_size():
    docs, _payload = load_corpus()
    assert len(docs) >= MIN_CORPUS_DOCS


def test_corpus_has_minimum_superseded_pairs():
    docs, _payload = load_corpus()
    superseded = sum(1 for d in docs if d.superseded_by)
    assert superseded >= MIN_SUPERSEDED_PAIRS


def test_questions_meet_minimum_count():
    cases, _payload = load_questions()
    assert len(cases) >= MIN_QUESTIONS


def test_every_question_has_gold_evidence_in_corpus():
    docs, _corpus_payload = load_corpus()
    cases, _q_payload = load_questions()
    doc_ids = {d.doc_id for d in docs}
    for case in cases:
        for evidence_id in case.expected["gold_evidence_doc_ids"]:
            assert evidence_id in doc_ids


def test_every_question_stale_doc_is_superseded():
    docs, _corpus_payload = load_corpus()
    cases, _q_payload = load_questions()
    docs_by_id = {d.doc_id: d for d in docs}
    for case in cases:
        stale_id = case.expected["stale_doc_id"]
        if stale_id:
            assert docs_by_id[stale_id].superseded_by is not None
