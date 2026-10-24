from __future__ import annotations

from labs.lab03_few_shot.data import load_eval_and_pool
from labs.lab03_few_shot.selectors import (
    select_boundary_focused,
    select_diverse_boundary,
    select_diverse_typical,
    select_misleading,
    select_random,
    select_redundant,
)


def _pool():
    _eval, pool, _e, _p = load_eval_and_pool()
    return pool


def test_select_diverse_boundary_respects_k():
    pool = _pool()
    assert select_diverse_boundary(pool, 0) == ()
    assert len(select_diverse_boundary(pool, 2)) == 2
    assert len(select_diverse_boundary(pool, 4)) == 4
    assert len(select_diverse_boundary(pool, 8)) == 8


def test_select_diverse_boundary_prefers_typical_before_boundary():
    pool = _pool()
    # Pool has 15 typical examples; asking for 4 should be satisfiable from typical alone.
    examples = select_diverse_boundary(pool, 4)
    typical_texts = {c.input_text for c in pool if c.metadata.get("purpose") == "typical"}
    assert all(ex.input_text in typical_texts for ex in examples)


def test_select_random_is_deterministic_for_fixed_seed():
    pool = _pool()
    a = select_random(pool, 4, seed=5)
    b = select_random(pool, 4, seed=5)
    assert a == b


def test_select_random_differs_across_seeds():
    pool = _pool()
    a = select_random(pool, 4, seed=1)
    b = select_random(pool, 4, seed=2)
    assert a != b


def test_select_redundant_returns_only_redundant_tagged():
    pool = _pool()
    examples = select_redundant(pool, 4)
    redundant_texts = {c.input_text for c in pool if c.metadata.get("purpose") == "redundant"}
    assert len(examples) == 4
    assert all(ex.input_text in redundant_texts for ex in examples)


def test_select_diverse_typical_covers_multiple_classes():
    pool = _pool()
    examples = select_diverse_typical(pool, 4)
    labels = {ex.output_text for ex in examples}
    assert len(labels) >= 3  # at least 3 distinct classes among 4 picks


def test_select_boundary_focused_covers_distinct_pairs():
    pool = _pool()
    examples = select_boundary_focused(pool, 4)
    assert len(examples) == 4
    # Each should come from a distinct confused pair (4 pairs exist in the pool).
    boundary_cases = [c for c in pool if c.metadata.get("purpose") == "boundary"]
    pair_keys = set()
    for ex in examples:
        matching = next(c for c in boundary_cases if c.input_text == ex.input_text)
        tag = next(t for t in matching.metadata["tags"] if t.startswith("confuses_"))
        pair_keys.add(tag)
    assert len(pair_keys) == 4


def test_select_misleading_returns_misleading_tagged():
    pool = _pool()
    examples = select_misleading(pool, 4)
    misleading_texts = {
        c.input_text for c in pool if c.metadata.get("purpose") == "misleading_candidate"
    }
    assert len(examples) == 4
    assert all(ex.input_text in misleading_texts for ex in examples)
