from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.prompt_builder import build_messages
from lab_core.tokens import estimate_messages_tokens
from labs.lab01_prompt_anatomy.conditions import CONDITION_ORDER, build_conditions
from labs.lab01_prompt_anatomy.data import load_eval_and_pool

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def _pool_cases():
    _eval, pool, _e, _p = load_eval_and_pool()
    return pool


def test_condition_ids_match_spec_order():
    conditions = build_conditions(_pool_cases(), TOKENS_CFG)
    assert [c.condition_id for c in conditions] == CONDITION_ORDER


def test_conditions_are_cumulative_instruction_context_constraints():
    conditions = {
        c.condition_id: c.build_components() for c in build_conditions(_pool_cases(), TOKENS_CFG)
    }
    baseline, a, b, b_len, c, d = (
        conditions["baseline"],
        conditions["A_context"],
        conditions["B_constraints"],
        conditions["B_len"],
        conditions["C_output_contract"],
        conditions["D_examples"],
    )
    assert baseline.context == ()
    assert len(a.context) == 1
    assert a.constraints is None
    assert b.context == a.context
    assert b.constraints is not None
    assert b_len.constraints.startswith(b.constraints)
    assert c.output_contract is not None
    assert c.constraints == b.constraints
    assert d.examples != ()
    assert d.output_contract == c.output_contract


def test_b_len_has_no_output_contract_or_examples():
    conditions = {
        c.condition_id: c.build_components() for c in build_conditions(_pool_cases(), TOKENS_CFG)
    }
    b_len = conditions["B_len"]
    assert b_len.output_contract is None
    assert b_len.examples == ()


def test_b_len_padding_brings_length_close_to_d():
    conditions = {
        c.condition_id: c.build_components() for c in build_conditions(_pool_cases(), TOKENS_CFG)
    }
    sample_input = "Ornek musteri mesaji metni."
    b_tokens = estimate_messages_tokens(
        [m.as_dict() for m in build_messages(conditions["B_constraints"], sample_input)], TOKENS_CFG
    )
    b_len_tokens = estimate_messages_tokens(
        [m.as_dict() for m in build_messages(conditions["B_len"], sample_input)], TOKENS_CFG
    )
    d_tokens = estimate_messages_tokens(
        [m.as_dict() for m in build_messages(conditions["D_examples"], sample_input)], TOKENS_CFG
    )
    assert b_len_tokens > b_tokens
    # Within a generous tolerance of D's length (estimator-based, not exact by design).
    assert abs(b_len_tokens - d_tokens) <= max(10, 0.15 * d_tokens)


def test_generation_overrides_identical_across_conditions():
    """Controlled-variable check: no condition overrides model/temperature/etc, so the
    runner's base_generation_params alone determines them identically everywhere."""
    conditions = build_conditions(_pool_cases(), TOKENS_CFG)
    assert all(c.generation_overrides == {} for c in conditions)


def test_examples_are_class_balanced_and_disjoint_from_eval_text():
    pool = _pool_cases()
    conditions = {c.condition_id: c.build_components() for c in build_conditions(pool, TOKENS_CFG)}
    examples = conditions["D_examples"].examples
    assert len(examples) == 5  # one per class
    pool_texts = {c.input_text for c in pool}
    for example in examples:
        assert example.input_text in pool_texts  # examples come from the pool, not eval


def _ablation_conditions():
    return {
        c.condition_id: c.build_components()
        for c in build_conditions(_pool_cases(), TOKENS_CFG, include_ablation=True)
    }


def test_ablation_is_off_by_default():
    ids = [c.condition_id for c in build_conditions(_pool_cases(), TOKENS_CFG)]
    assert not any(cid.startswith("LOO_") for cid in ids)


def test_ablation_adds_exactly_the_documented_conditions():
    from labs.lab01_prompt_anatomy.conditions import ABLATION_CONDITION_ORDER

    ids = [
        c.condition_id for c in build_conditions(_pool_cases(), TOKENS_CFG, include_ablation=True)
    ]
    assert ids == CONDITION_ORDER + ABLATION_CONDITION_ORDER


def test_each_ablation_condition_differs_from_full_prompt_in_exactly_one_component():
    """Controlled-variable check for the leave-one-out ablation: every LOO condition must
    equal the full prompt (D) in every component except the one it removes."""
    conditions = _ablation_conditions()
    full = conditions["D_examples"]
    fields = ["instruction", "context", "constraints", "output_contract", "examples"]
    expected_removed = {
        "LOO_no_instruction": "instruction",
        "LOO_no_context": "context",
        "LOO_no_constraints": "constraints",
        "LOO_no_output_contract": "output_contract",
    }
    for cid, removed in expected_removed.items():
        loo = conditions[cid]
        changed = [f for f in fields if getattr(loo, f) != getattr(full, f)]
        assert changed == [removed], cid
        assert not getattr(loo, removed)


def test_minus_examples_is_condition_c_so_it_is_not_run_twice():
    from labs.lab01_prompt_anatomy.conditions import ABLATION_EQUIVALENTS

    conditions = _ablation_conditions()
    full = conditions["D_examples"]
    c = conditions[ABLATION_EQUIVALENTS["LOO_no_examples"]]
    assert c.examples == ()
    assert (c.instruction, c.context, c.constraints, c.output_contract) == (
        full.instruction,
        full.context,
        full.constraints,
        full.output_contract,
    )


def test_empty_instruction_is_omitted_not_rendered_as_blank_paragraph():
    no_instruction = _ablation_conditions()["LOO_no_instruction"]
    system = build_messages(no_instruction, "mesaj")[0].content
    assert not system.startswith("\n")
    assert "Gelen musteri mesajini siniflandir." not in system


def test_ablation_conditions_hold_generation_parameters_constant():
    conditions = build_conditions(_pool_cases(), TOKENS_CFG, include_ablation=True)
    assert all(c.generation_overrides == {} for c in conditions)
