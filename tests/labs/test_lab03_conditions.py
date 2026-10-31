from __future__ import annotations

from labs.lab03_few_shot.conditions import CONDITION_ORDER, build_conditions
from labs.lab03_few_shot.data import load_eval_and_pool


def _pool():
    _eval, pool, _e, _p = load_eval_and_pool()
    return pool


def test_condition_ids_match_spec_order():
    assert [c.condition_id for c in build_conditions(_pool())] == CONDITION_ORDER


def test_count_series_has_increasing_example_counts():
    components = {c.condition_id: c.build_components() for c in build_conditions(_pool())}
    assert len(components["count_0"].examples) == 0
    assert len(components["count_2"].examples) == 2
    assert len(components["count_4"].examples) == 4
    assert len(components["count_8"].examples) == 8


def test_quality_series_all_have_k_equals_4():
    components = {c.condition_id: c.build_components() for c in build_conditions(_pool())}
    for cid in [
        "quality_random_seed1",
        "quality_random_seed2",
        "quality_random_seed3",
        "quality_redundant",
        "quality_diverse_typical",
        "quality_boundary_focused",
        "quality_misleading",
    ]:
        assert len(components[cid].examples) == 4, cid


def test_instruction_context_constraints_output_contract_identical_across_conditions():
    """Only `examples` is allowed to vary between conditions — count and quality are each
    varied one at a time, never both."""
    components = {c.condition_id: c.build_components() for c in build_conditions(_pool())}
    reference = components["count_0"]
    for cid, comp in components.items():
        assert comp.instruction == reference.instruction, cid
        assert comp.context == reference.context, cid
        assert comp.constraints == reference.constraints, cid
        assert comp.output_contract == reference.output_contract, cid


def test_generation_overrides_identical_across_conditions():
    assert all(c.generation_overrides == {} for c in build_conditions(_pool()))


def test_random_seeds_produce_different_examples():
    components = {c.condition_id: c.build_components() for c in build_conditions(_pool())}
    seed1 = components["quality_random_seed1"].examples
    seed2 = components["quality_random_seed2"].examples
    assert seed1 != seed2


def _with_order():
    return {
        c.condition_id: c.build_components()
        for c in build_conditions(_pool(), include_order_effect=True)
    }


def test_order_series_is_off_by_default():
    ids = [c.condition_id for c in build_conditions(_pool())]
    assert not any(cid.startswith("order_") for cid in ids)


def test_order_series_appends_documented_conditions():
    from labs.lab03_few_shot.conditions import ORDER_CONDITION_ORDER

    ids = [c.condition_id for c in build_conditions(_pool(), include_order_effect=True)]
    assert ids == CONDITION_ORDER + ORDER_CONDITION_ORDER


def test_order_conditions_use_the_identical_example_set_in_a_different_order():
    """Controlled-variable check: only the order varies — same examples (as a multiset),
    same instruction/context/constraints/contract — and each order is genuinely different."""
    from labs.lab03_few_shot.conditions import ORDER_CONDITION_ORDER, ORDER_REFERENCE_CONDITION_ID

    components = _with_order()
    reference = components[ORDER_REFERENCE_CONDITION_ID]
    seen_orders = {reference.examples}
    for cid in ORDER_CONDITION_ORDER:
        variant = components[cid]
        assert sorted(variant.examples, key=repr) == sorted(reference.examples, key=repr)
        assert variant.examples not in seen_orders, cid
        seen_orders.add(variant.examples)
        assert (variant.instruction, variant.context, variant.constraints) == (
            reference.instruction,
            reference.context,
            reference.constraints,
        )
        assert variant.output_contract == reference.output_contract


def test_reorder_examples_rejects_invalid_permutations():
    import pytest

    from labs.lab03_few_shot.conditions import reorder_examples

    with pytest.raises(ValueError):
        reorder_examples(("a", "b", "c"), (0, 0, 1))
    assert reorder_examples(("a", "b", "c"), (2, 0, 1)) == ("c", "a", "b")
