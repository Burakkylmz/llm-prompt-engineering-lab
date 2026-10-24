from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.experiment_runner import Case
from lab_core.tokens import estimate_tokens
from labs.lab05_context_rot.conditions import (
    DEFAULT_LENGTHS_TOKENS,
    build_conditions,
    condition_order,
)

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)
FILLER = [f"Bu {i}. dolgu cumlesidir ve genel sirket konularini anlatir." for i in range(50)]


def _case():
    return Case(
        case_id="c1",
        input_text="Soru metni?",
        expected={"gold_answer": "750000 TL", "near_miss_answer": "500000 TL"},
        metadata={
            "fact_sentence": "HEDEF GERCEK: deger 750000 TL'dir.",
            "near_miss_sentence": "YANILTICI: deger 500000 TL'dir.",
        },
    )


def test_condition_ids_match_default_lengths():
    conditions = build_conditions(FILLER, TOKENS_CFG)
    assert [c.condition_id for c in conditions] == condition_order()
    assert condition_order() == [f"length_{length}" for length in DEFAULT_LENGTHS_TOKENS]


def test_instruction_identical_across_all_lengths():
    conditions = build_conditions(FILLER, TOKENS_CFG)
    components = [c.build_components() for c in conditions]
    reference = components[0]
    for comp in components[1:]:
        assert comp.instruction == reference.instruction
        assert comp.constraints == reference.constraints
        assert comp.output_contract == reference.output_contract


def test_fact_appears_near_relative_middle_position_at_every_length():
    conditions = {
        c.condition_id: c for c in build_conditions(FILLER, TOKENS_CFG, lengths=[1000, 4000])
    }
    case = _case()
    for cid in ("length_1000", "length_4000"):
        user_input, _untrusted = conditions[cid].build_user_input(case)
        fact_pos = user_input.index("HEDEF GERCEK")
        ratio = fact_pos / len(user_input)
        assert 0.3 <= ratio <= 0.7, f"{cid}: ratio={ratio}"


def test_actual_length_approaches_target_for_each_condition():
    conditions = {
        c.condition_id: c for c in build_conditions(FILLER, TOKENS_CFG, lengths=[1000, 4000])
    }
    case = _case()
    for cid, target in [("length_1000", 1000), ("length_4000", 4000)]:
        user_input, _untrusted = conditions[cid].build_user_input(case)
        tokens = estimate_tokens(user_input, TOKENS_CFG)
        assert abs(tokens - target) <= max(50, target * 0.1)


def test_builds_are_deterministic_for_same_case_and_length():
    conditions = build_conditions(FILLER, TOKENS_CFG, lengths=[1000])
    case = _case()
    a, _ = conditions[0].build_user_input(case)
    b, _ = conditions[0].build_user_input(case)
    assert a == b
