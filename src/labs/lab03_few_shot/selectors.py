"""Deterministic example-selection strategies (spec Section 11 LAB 03).

Count and quality are never varied together: `select_diverse_boundary` is the one fixed
strategy used across the whole count series (0/2/4/8); every quality-series selector fixes
k=4 and varies only *which* 4 examples are chosen.
"""

from __future__ import annotations

import random

from lab_core.experiment_runner import Case
from lab_core.prompt_builder import Example
from labs.lab03_few_shot.data import LABELS


def _to_example(case: Case) -> Example:
    return Example(input_text=case.input_text, output_text=f"ETIKET: {case.expected['label']}")


def _round_robin_by_label(cases: list[Case], k: int) -> list[Case]:
    by_label: dict[str, list[Case]] = {label: [] for label in LABELS}
    for case in cases:
        by_label.setdefault(case.expected["label"], []).append(case)
    iters = {label: iter(items) for label, items in by_label.items()}
    result: list[Case] = []
    while len(result) < k and iters:
        for label in list(iters.keys()):
            if len(result) >= k:
                break
            try:
                result.append(next(iters[label]))
            except StopIteration:
                del iters[label]
    return result


def select_diverse_boundary(pool: list[Case], k: int) -> tuple[Example, ...]:
    """Fixed strategy for the count series: typical examples first (round-robin across
    classes), topped up with boundary examples if more are needed."""
    if k <= 0:
        return ()
    typical = [c for c in pool if c.metadata.get("purpose") == "typical"]
    boundary = [c for c in pool if c.metadata.get("purpose") == "boundary"]

    chosen = _round_robin_by_label(typical, k)
    if len(chosen) < k:
        chosen += _round_robin_by_label(boundary, k - len(chosen))
    return tuple(_to_example(c) for c in chosen[:k])


def select_random(pool: list[Case], k: int, seed: int) -> tuple[Example, ...]:
    rng = random.Random(seed)
    chosen = rng.sample(pool, min(k, len(pool)))
    return tuple(_to_example(c) for c in chosen)


def select_redundant(pool: list[Case], k: int) -> tuple[Example, ...]:
    redundant = [c for c in pool if c.metadata.get("purpose") == "redundant"]
    return tuple(_to_example(c) for c in redundant[:k])


def select_diverse_typical(pool: list[Case], k: int) -> tuple[Example, ...]:
    typical = [c for c in pool if c.metadata.get("purpose") == "typical"]
    chosen = _round_robin_by_label(typical, k)
    return tuple(_to_example(c) for c in chosen[:k])


def select_boundary_focused(pool: list[Case], k: int) -> tuple[Example, ...]:
    """One example per confused class-pair (identified by the `confuses_<a>_<b>` tag),
    so k=4 covers 4 distinct boundary pairs rather than both halves of fewer pairs."""
    boundary = [c for c in pool if c.metadata.get("purpose") == "boundary"]
    seen_pairs: set[str] = set()
    chosen: list[Case] = []
    for case in boundary:
        pair_tags = [t for t in case.metadata.get("tags", []) if t.startswith("confuses_")]
        pair_key = pair_tags[0] if pair_tags else case.case_id
        if pair_key not in seen_pairs:
            chosen.append(case)
            seen_pairs.add(pair_key)
        if len(chosen) >= k:
            break
    return tuple(_to_example(c) for c in chosen[:k])


def select_misleading(pool: list[Case], k: int) -> tuple[Example, ...]:
    misleading = [c for c in pool if c.metadata.get("purpose") == "misleading_candidate"]
    return tuple(_to_example(c) for c in misleading[:k])
