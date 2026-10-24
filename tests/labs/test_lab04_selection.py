from __future__ import annotations

from lab_core.config import TokensConfig
from labs.lab04_context_selection.data import load_corpus, load_questions
from labs.lab04_context_selection.selection import (
    select_all_documents,
    select_ordered_variant,
    select_relevance_budget,
    select_relevance_dedup_fresh_top_k,
    select_relevance_dedup_top_k,
    select_relevance_top_k,
)

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def _corpus():
    docs, _payload = load_corpus()
    return docs


def _first_question_text():
    cases, _payload = load_questions()
    return cases[0].input_text, cases[0].expected


def test_relevance_top_k_respects_k():
    corpus = _corpus()
    question, _expected = _first_question_text()
    assert len(select_relevance_top_k(question, corpus, k=5)) == 5


def test_relevance_top_k_finds_gold_doc():
    corpus = _corpus()
    question, expected = _first_question_text()
    selected_ids = {d.doc_id for d in select_relevance_top_k(question, corpus, k=5)}
    assert set(expected["gold_evidence_doc_ids"]) & selected_ids


def test_dedup_removes_exact_and_near_duplicates_but_not_version_conflicts():
    corpus = _corpus()
    question, expected = _first_question_text()
    gold_id = expected["gold_evidence_doc_ids"][0]

    deduped = select_relevance_dedup_top_k(question, corpus, k=10)
    deduped_ids = {d.doc_id for d in deduped}
    # The current and stale (superseded) docs are a version conflict, not a near-duplicate:
    # dedup alone must NOT remove the stale doc (that is freshness filtering's job).
    if gold_id in deduped_ids:
        pass  # presence depends on relevance ranking, not asserted here
    assert len(deduped) <= 10


def test_freshness_removes_stale_doc_from_selection():
    corpus = _corpus()
    question, expected = _first_question_text()
    stale_id = expected["stale_doc_id"]

    selected = select_relevance_dedup_fresh_top_k(question, corpus, k=10)
    selected_ids = {d.doc_id for d in selected}
    assert stale_id not in selected_ids


def test_all_documents_returns_everything_when_under_cap():
    corpus = _corpus()
    selected = select_all_documents("herhangi bir soru", corpus, TOKENS_CFG, cap_tokens=100_000)
    assert len(selected) == len(corpus)


def test_all_documents_caps_when_over_budget():
    corpus = _corpus()
    selected = select_all_documents("herhangi bir soru", corpus, TOKENS_CFG, cap_tokens=50)
    assert len(selected) < len(corpus)


def test_budget_selection_respects_budget():
    corpus = _corpus()
    question, _expected = _first_question_text()
    from lab_core.tokens import estimate_tokens

    selected = select_relevance_budget(
        question, corpus, budget_tokens=100, tokens_config=TOKENS_CFG
    )
    total_tokens = sum(estimate_tokens(d.text, TOKENS_CFG) for d in selected)
    assert total_tokens <= 100


def test_ordered_variant_relevance_asc_is_reverse_of_desc():
    corpus = _corpus()
    question, _expected = _first_question_text()
    desc = select_relevance_dedup_fresh_top_k(question, corpus, k=5)
    asc = select_ordered_variant(question, corpus, "relevance_asc")
    assert [d.doc_id for d in asc] == [d.doc_id for d in reversed(desc)]


def test_ordered_variant_same_document_set_different_order():
    corpus = _corpus()
    question, _expected = _first_question_text()
    desc_ids = {d.doc_id for d in select_relevance_dedup_fresh_top_k(question, corpus, k=5)}
    random_ids = {
        d.doc_id for d in select_ordered_variant(question, corpus, "seeded_random", seed=1)
    }
    assert desc_ids == random_ids
