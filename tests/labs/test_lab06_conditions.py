from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.experiment_runner import Case
from lab_core.tokens import estimate_tokens
from labs.lab06_lost_in_middle.conditions import (
    DEFAULT_POSITIONS,
    FIXED_LENGTH_TOKENS,
    build_conditions,
    condition_order,
)

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)
FILLER = [f"Bu {i}. dolgu cumlesidir ve genel sirket konularini anlatir." for i in range(80)]


def _case():
    return Case(
        case_id="c1",
        input_text="Soru metni?",
        expected={"gold_answer": "750000 TL", "near_miss_answer": "500000 TL"},
        metadata={
            "fact_sentence": "HEDEF GERCEK deger 750000 TL'dir.",
            "near_miss_sentence": "YANILTICI deger 500000 TL'dir.",
            "clause_id": "MADDE-01",
        },
    )


def test_condition_ids_match_positions():
    conditions = build_conditions(FILLER, TOKENS_CFG)
    assert [c.condition_id for c in conditions] == condition_order()
    assert len(conditions) == len(DEFAULT_POSITIONS)


def test_all_conditions_share_identical_total_length_target():
    """Controlled-variable check: length is fixed across every position condition."""
    conditions = build_conditions(FILLER, TOKENS_CFG)
    case = _case()
    lengths = []
    for condition in conditions:
        user_input, _untrusted = condition.build_user_input(case)
        lengths.append(estimate_tokens(user_input, TOKENS_CFG))
    for length in lengths:
        assert abs(length - FIXED_LENGTH_TOKENS) <= max(50, FIXED_LENGTH_TOKENS * 0.1)


def test_position_000_places_fact_near_the_start():
    conditions = {c.condition_id: c for c in build_conditions(FILLER, TOKENS_CFG)}
    user_input, _ = conditions["position_000"].build_user_input(_case())
    ratio = user_input.index("HEDEF GERCEK") / len(user_input)
    assert ratio < 0.1


def test_position_100_places_fact_near_the_end():
    conditions = {c.condition_id: c for c in build_conditions(FILLER, TOKENS_CFG)}
    user_input, _ = conditions["position_100"].build_user_input(_case())
    ratio = user_input.index("HEDEF GERCEK") / len(user_input)
    assert ratio > 0.9


def test_position_050_places_fact_near_the_middle():
    conditions = {c.condition_id: c for c in build_conditions(FILLER, TOKENS_CFG)}
    user_input, _ = conditions["position_050"].build_user_input(_case())
    ratio = user_input.index("HEDEF GERCEK") / len(user_input)
    assert 0.3 < ratio < 0.7


def test_instruction_identical_across_all_positions():
    conditions = build_conditions(FILLER, TOKENS_CFG)
    components = [c.build_components() for c in conditions]
    reference = components[0]
    for comp in components[1:]:
        assert comp.instruction == reference.instruction
        assert comp.output_contract == reference.output_contract
