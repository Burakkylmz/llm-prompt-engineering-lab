from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.context_manager import (
    Document,
    assemble_fixed_length,
    deduplicate,
    filter_fresh,
    order_documents,
    score_relevance,
    select_within_budget,
)
from lab_core.tokens import estimate_tokens

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def _doc(doc_id, text, effective_date="2026-01-01", superseded_by=None):
    return Document(
        doc_id=doc_id, text=text, effective_date=effective_date, superseded_by=superseded_by
    )


def test_score_relevance_ranks_matching_doc_higher():
    docs = [
        _doc("a", "izin politikasi yillik otuz gun ucretli izin hakki tanimlar"),
        _doc("b", "harcama politikasi seyahat masraflarinin geri odenmesini aciklar"),
    ]
    scores = score_relevance("yillik izin hakki kac gun", docs)
    ranked_ids = [doc_id for doc_id, _score in scores]
    assert ranked_ids[0] == "a"


def test_score_relevance_empty_docs_returns_empty():
    assert score_relevance("sorgu", []) == []


def test_score_relevance_no_matching_terms_still_returns_all_docs():
    docs = [_doc("a", "tamamen ilgisiz bir metin"), _doc("b", "baska ilgisiz bir metin")]
    scores = score_relevance("hic eslesmeyen kelimeler", docs)
    assert {doc_id for doc_id, _ in scores} == {"a", "b"}


def test_deduplicate_removes_exact_duplicates():
    docs = [_doc("a", "ayni metin icerigi"), _doc("b", "ayni metin icerigi")]
    deduped = deduplicate(docs)
    assert len(deduped) == 1
    assert deduped[0].doc_id == "a"  # first-seen is kept


def test_deduplicate_removes_near_duplicates():
    docs = [
        _doc("a", "izin politikasi yillik otuz gun ucretli izin hakki tanimlar calisanlara"),
        _doc("b", "izin politikasi yillik otuz gun ucretli izin hakki tanimlar personele"),
    ]
    deduped = deduplicate(docs, threshold=0.6)
    assert len(deduped) == 1


def test_deduplicate_keeps_genuinely_different_docs():
    docs = [
        _doc("a", "izin politikasi aciklamasi"),
        _doc("b", "harcama politikasi aciklamasi farkli konu"),
    ]
    deduped = deduplicate(docs, threshold=0.9)
    assert len(deduped) == 2


def test_filter_fresh_drops_superseded_docs():
    docs = [
        _doc("old", "eski politika metni", superseded_by="new"),
        _doc("new", "yeni politika metni"),
    ]
    fresh = filter_fresh(docs)
    assert [d.doc_id for d in fresh] == ["new"]


def test_filter_fresh_keeps_docs_with_no_superseding_relationship():
    docs = [_doc("a", "metin a"), _doc("b", "metin b")]
    assert filter_fresh(docs) == docs


def test_order_documents_relevance_desc_is_identity():
    docs = [_doc("a", "x"), _doc("b", "y")]
    assert order_documents(docs, "relevance_desc") == docs


def test_order_documents_relevance_asc_reverses():
    docs = [_doc("a", "x"), _doc("b", "y")]
    assert order_documents(docs, "relevance_asc") == list(reversed(docs))


def test_order_documents_seeded_random_is_deterministic():
    docs = [_doc(str(i), f"text {i}") for i in range(10)]
    a = order_documents(docs, "seeded_random", seed=42)
    b = order_documents(docs, "seeded_random", seed=42)
    assert [d.doc_id for d in a] == [d.doc_id for d in b]


def test_order_documents_rejects_unknown_strategy():
    import pytest

    with pytest.raises(ValueError):
        order_documents([], "nonsense")


def test_select_within_budget_stops_at_limit():
    docs = [_doc("a", "a" * 40), _doc("b", "b" * 40), _doc("c", "c" * 40)]
    docs_by_id = {d.doc_id: d for d in docs}
    scored = [("a", 3.0), ("b", 2.0), ("c", 1.0)]
    single_doc_tokens = 40 // 4  # default_chars_per_token=4.0, Turkish text but single-char repeats
    selected = select_within_budget(
        scored, docs_by_id, budget_tokens=single_doc_tokens + 2, tokens_config=TOKENS_CFG
    )
    assert len(selected) == 1
    assert selected[0].doc_id == "a"


_FILLER = [f"Bu {i}. dolgu cumlesidir ve genel sirket konularini anlatir." for i in range(10)]
_NEAR_MISS = ["Proje butcesi 500000 TL olarak belirlenmistir ancak bu rakam yanlistir."]


def test_assemble_fixed_length_reaches_approximate_target_length():
    text = assemble_fixed_length(
        target_fact_sentence="Proje butcesi gercekte 750000 TL olarak onaylanmistir.",
        filler_sentences=_FILLER,
        near_miss_sentences=_NEAR_MISS,
        target_length_tokens=200,
        relative_position=0.5,
        tokens_config=TOKENS_CFG,
        seed=1,
    )
    tokens = estimate_tokens(text, TOKENS_CFG)
    assert abs(tokens - 200) <= 20


def test_assemble_fixed_length_places_fact_near_relative_position():
    text = assemble_fixed_length(
        target_fact_sentence="Proje butcesi gercekte 750000 TL olarak onaylanmistir.",
        filler_sentences=_FILLER,
        near_miss_sentences=[],
        target_length_tokens=300,
        relative_position=0.0,
        tokens_config=TOKENS_CFG,
        seed=2,
    )
    assert text.startswith("Proje butcesi gercekte 750000 TL")


def test_assemble_fixed_length_at_end_position():
    text = assemble_fixed_length(
        target_fact_sentence="Proje butcesi gercekte 750000 TL olarak onaylanmistir.",
        filler_sentences=_FILLER,
        near_miss_sentences=[],
        target_length_tokens=300,
        relative_position=1.0,
        tokens_config=TOKENS_CFG,
        seed=2,
    )
    assert text.endswith("Proje butcesi gercekte 750000 TL olarak onaylanmistir.")


def test_assemble_fixed_length_is_deterministic_for_fixed_seed():
    kwargs = dict(
        target_fact_sentence="x",
        filler_sentences=_FILLER,
        near_miss_sentences=_NEAR_MISS,
        target_length_tokens=150,
        relative_position=0.3,
        tokens_config=TOKENS_CFG,
        seed=7,
    )
    assert assemble_fixed_length(**kwargs) == assemble_fixed_length(**kwargs)


def test_assemble_fixed_length_rejects_invalid_position():
    import pytest

    with pytest.raises(ValueError):
        assemble_fixed_length(
            target_fact_sentence="x",
            filler_sentences=_FILLER,
            near_miss_sentences=[],
            target_length_tokens=100,
            relative_position=1.5,
            tokens_config=TOKENS_CFG,
        )


def test_select_within_budget_skips_oversized_doc_but_fills_with_smaller_ones():
    docs_by_id = {
        "big": _doc("big", "x" * 400),
        "small": _doc("small", "y" * 20),
    }
    scored = [("big", 5.0), ("small", 1.0)]
    selected = select_within_budget(scored, docs_by_id, budget_tokens=10, tokens_config=TOKENS_CFG)
    assert [d.doc_id for d in selected] == ["small"]
