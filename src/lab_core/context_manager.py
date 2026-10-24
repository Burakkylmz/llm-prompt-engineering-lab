"""Context selection primitives (spec Section 8): relevance scoring, deduplication,
freshness filtering, ordering, and token-budget selection. Pure functions over `Document` —
no lab-specific logic. Built in M3 for Lab 04, the first lab that actually needs retrieval
(Lab 01's "context" was one static block; see docs/decisions.md for why this module was
deferred from M2).
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field

from lab_core.config import TokensConfig
from lab_core.evaluation import normalize_text_tr
from lab_core.text_similarity import shingle_jaccard
from lab_core.tokens import estimate_tokens


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str
    effective_date: str
    superseded_by: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


def _tokenize(text: str) -> list[str]:
    return normalize_text_tr(text).split()


def score_relevance(query: str, docs: list[Document]) -> list[tuple[str, float]]:
    """Okapi BM25 (k1=1.5, b=0.75) over Turkish-normalized whitespace tokens. Returns
    (doc_id, score) pairs sorted by descending score."""
    if not docs:
        return []
    k1, b = 1.5, 0.75
    query_terms = _tokenize(query)
    doc_tokens = {doc.doc_id: _tokenize(doc.text) for doc in docs}
    doc_lengths = {doc_id: len(tokens) for doc_id, tokens in doc_tokens.items()}
    avg_len = sum(doc_lengths.values()) / len(doc_lengths) if doc_lengths else 1.0
    n_docs = len(docs)

    doc_freq: Counter[str] = Counter()
    for tokens in doc_tokens.values():
        for term in set(tokens):
            doc_freq[term] += 1
    idf = {
        term: math.log(1 + (n_docs - freq + 0.5) / (freq + 0.5)) for term, freq in doc_freq.items()
    }

    scores: list[tuple[str, float]] = []
    for doc_id, tokens in doc_tokens.items():
        term_freq = Counter(tokens)
        score = 0.0
        doc_len = doc_lengths[doc_id] or 1
        for term in query_terms:
            freq = term_freq.get(term, 0)
            if freq == 0:
                continue
            numerator = idf.get(term, 0.0) * freq * (k1 + 1)
            denominator = freq + k1 * (1 - b + b * doc_len / avg_len)
            score += numerator / denominator
        scores.append((doc_id, score))

    scores.sort(key=lambda pair: -pair[1])
    return scores


def deduplicate(docs: list[Document], threshold: float = 0.85) -> list[Document]:
    """Exact-hash dedup first (identical text), then near-duplicate removal via
    shingle-Jaccard similarity. Keeps the first-seen document of each duplicate group
    (stable, deterministic — no randomness)."""
    seen_exact: set[str] = set()
    exact_deduped: list[Document] = []
    for doc in docs:
        if doc.text in seen_exact:
            continue
        seen_exact.add(doc.text)
        exact_deduped.append(doc)

    kept: list[Document] = []
    for doc in exact_deduped:
        if any(shingle_jaccard(doc.text, other.text) >= threshold for other in kept):
            continue
        kept.append(doc)
    return kept


def filter_fresh(docs: list[Document]) -> list[Document]:
    """Drops any document that has itself been superseded (i.e. has a non-null
    `superseded_by`, meaning another document replaces it) — not the replacement."""
    return [doc for doc in docs if doc.superseded_by is None]


def order_documents(docs: list[Document], strategy: str, seed: int = 0) -> list[Document]:
    """`strategy` is one of relevance_desc | relevance_asc | seeded_random | original.
    `docs` is assumed to already be in relevance-descending order on input (as produced by
    `score_relevance` + a lookup) for the relevance_desc/asc strategies; `original` and
    `seeded_random` are agnostic to input order."""
    if strategy == "relevance_desc":
        return list(docs)
    if strategy == "relevance_asc":
        return list(reversed(docs))
    if strategy == "seeded_random":
        shuffled = list(docs)
        random.Random(seed).shuffle(shuffled)
        return shuffled
    if strategy == "original":
        return list(docs)
    raise ValueError(f"Unknown ordering strategy: {strategy!r}")


def assemble_fixed_length(
    *,
    target_fact_sentence: str,
    filler_sentences: list[str],
    near_miss_sentences: list[str],
    target_length_tokens: int,
    relative_position: float,
    tokens_config: TokensConfig,
    near_miss_density: float = 0.1,
    seed: int = 0,
) -> str:
    """Builds coherent filler text of approximately `target_length_tokens`, with
    `target_fact_sentence` inserted at `relative_position` (0.0 = start, 1.0 = end) and a
    `near_miss_density` fraction of the surrounding sentences replaced by near-miss
    distractors (same fact type, different value). Used by Lab 05 (varies length at fixed
    position) and Lab 06 (varies position at fixed length) — one implementation, not two.

    Deterministic for a fixed seed. `filler_sentences` is cycled (reshuffled on each full
    pass) rather than repeated verbatim in a fixed order, so a long assembled text does not
    show an obvious repeating block.
    """
    if not 0.0 <= relative_position <= 1.0:
        raise ValueError("relative_position must be between 0.0 and 1.0")
    if not filler_sentences:
        raise ValueError("filler_sentences must be non-empty")

    rng = random.Random(seed)
    fact_tokens = estimate_tokens(target_fact_sentence, tokens_config)
    budget_for_filler = max(0, target_length_tokens - fact_tokens)

    stream: list[str] = []
    used_tokens = 0
    pass_count = 0
    while used_tokens < budget_for_filler:
        pool = list(filler_sentences)
        rng.shuffle(pool)
        pass_count += 1
        for sentence in pool:
            if used_tokens >= budget_for_filler:
                break
            if near_miss_sentences and rng.random() < near_miss_density:
                sentence = near_miss_sentences[rng.randrange(len(near_miss_sentences))]
            stream.append(sentence)
            used_tokens += estimate_tokens(sentence, tokens_config)
        if pass_count > 200:  # safety guard against a pathologically tiny filler pool
            break

    insert_at = round(relative_position * len(stream))
    insert_at = max(0, min(insert_at, len(stream)))
    stream.insert(insert_at, target_fact_sentence)
    return " ".join(stream)


def select_within_budget(
    scored_docs: list[tuple[str, float]],
    docs_by_id: dict[str, Document],
    budget_tokens: int,
    tokens_config: TokensConfig,
) -> list[Document]:
    """Greedy selection by descending relevance score until the next document would exceed
    the token budget. `scored_docs` must already be sorted by descending score."""
    selected: list[Document] = []
    used_tokens = 0
    for doc_id, _score in scored_docs:
        doc = docs_by_id[doc_id]
        doc_tokens = estimate_tokens(doc.text, tokens_config)
        if used_tokens + doc_tokens > budget_tokens:
            continue
        selected.append(doc)
        used_tokens += doc_tokens
    return selected
