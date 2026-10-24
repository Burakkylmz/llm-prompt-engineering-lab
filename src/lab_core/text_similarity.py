"""Shingle-Jaccard near-duplicate text similarity.

Shared by the dataset leakage check (spec Section 9.1: no eval item may be identical or
near-duplicate to an example-pool item) and, from Lab 04 onward, by the Context Manager's
near-duplicate document deduplication (spec Section 8) — one implementation, not two.
"""

from __future__ import annotations

from lab_core.evaluation import normalize_text_tr


def _shingles(text: str, k: int) -> set[str]:
    words = normalize_text_tr(text).split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def shingle_jaccard(text_a: str, text_b: str, k: int = 5) -> float:
    """Jaccard similarity of k-word shingle sets, after Turkish-aware normalization.
    Returns 1.0 for two empty strings (trivially identical), 0.0 if only one is empty."""
    shingles_a = _shingles(text_a, k)
    shingles_b = _shingles(text_b, k)
    if not shingles_a and not shingles_b:
        return 1.0
    if not shingles_a or not shingles_b:
        return 0.0
    intersection = len(shingles_a & shingles_b)
    union = len(shingles_a | shingles_b)
    return intersection / union
