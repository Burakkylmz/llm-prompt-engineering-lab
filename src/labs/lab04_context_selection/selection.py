"""Per-condition context-selection strategies, built from `lab_core.context_manager`'s
primitives. Each function takes a query and the full corpus and returns the documents that
condition would actually include in the prompt for that query."""

from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.context_manager import (
    Document,
    deduplicate,
    filter_fresh,
    order_documents,
    score_relevance,
    select_within_budget,
)
from lab_core.tokens import estimate_tokens

TOP_K = 5
DEDUP_CANDIDATE_POOL = 10


def select_all_documents(
    query: str, corpus: list[Document], tokens_config: TokensConfig, cap_tokens: int
) -> list[Document]:
    """No relevance filtering at all — original corpus order, capped only if the whole
    corpus would exceed `cap_tokens` (spec: "if this exceeds the per-request limit, cap it
    and document the cap")."""
    total = sum(estimate_tokens(doc.text, tokens_config) for doc in corpus)
    if total <= cap_tokens:
        return list(corpus)
    selected: list[Document] = []
    used = 0
    for doc in corpus:
        doc_tokens = estimate_tokens(doc.text, tokens_config)
        if used + doc_tokens > cap_tokens:
            continue
        selected.append(doc)
        used += doc_tokens
    return selected


def select_relevance_top_k(query: str, corpus: list[Document], k: int = TOP_K) -> list[Document]:
    scored = score_relevance(query, corpus)
    docs_by_id = {doc.doc_id: doc for doc in corpus}
    return [docs_by_id[doc_id] for doc_id, _score in scored[:k]]


def select_relevance_dedup_top_k(
    query: str, corpus: list[Document], k: int = TOP_K
) -> list[Document]:
    scored = score_relevance(query, corpus)
    docs_by_id = {doc.doc_id: doc for doc in corpus}
    candidates = [docs_by_id[doc_id] for doc_id, _score in scored[:DEDUP_CANDIDATE_POOL]]
    deduped = deduplicate(candidates)
    return deduped[:k]


def select_relevance_dedup_fresh_top_k(
    query: str, corpus: list[Document], k: int = TOP_K
) -> list[Document]:
    scored = score_relevance(query, corpus)
    docs_by_id = {doc.doc_id: doc for doc in corpus}
    candidates = [docs_by_id[doc_id] for doc_id, _score in scored[:DEDUP_CANDIDATE_POOL]]
    fresh = filter_fresh(candidates)
    deduped = deduplicate(fresh)
    return deduped[:k]


def select_relevance_budget(
    query: str, corpus: list[Document], budget_tokens: int, tokens_config: TokensConfig
) -> list[Document]:
    """Greedy relevance selection under a token budget (the budget series)."""
    scored = score_relevance(query, corpus)
    docs_by_id = {doc.doc_id: doc for doc in corpus}
    return select_within_budget(scored, docs_by_id, budget_tokens, tokens_config)


def select_ordered_variant(
    query: str, corpus: list[Document], strategy: str, seed: int = 0
) -> list[Document]:
    """The fixed relevance+dedup+freshness top-k set, re-ordered (the ordering series)."""
    base = select_relevance_dedup_fresh_top_k(query, corpus, TOP_K)
    return order_documents(base, strategy, seed=seed)
