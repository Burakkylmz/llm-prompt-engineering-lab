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
