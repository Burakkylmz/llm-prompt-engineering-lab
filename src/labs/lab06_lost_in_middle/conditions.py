"""Lab 06's position-series conditions (spec Section 11 LAB 06): a fixed total context
length, varying only the target fact's relative position. Kept separate from Lab 05, which
varies length at a fixed position — stated in both labs' READMEs.
"""

from __future__ import annotations

import hashlib

from lab_core.context_manager import assemble_fixed_length
from lab_core.experiment_runner import Case, Condition
from lab_core.prompt_builder import PromptComponents

INSTRUCTION = "Asagidaki metinde gecen bilgiye dayanarak soruyu cevapla."
CONSTRAINTS = (
    "Sadece metinde acikca belirtilen bilgiyi kullan. Kullandigin maddenin numarasini belirt."
)
OUTPUT_CONTRACT = (
    "Cevabini TAM OLARAK su formatta ver: 'CEVAP: <deger> | MADDE: <numara>' "
    "(metinde bulunamiyorsa: 'CEVAP: BULUNAMADI | MADDE: YOK')"
)
_COMPONENTS = PromptComponents(
    instruction=INSTRUCTION, constraints=CONSTRAINTS, output_contract=OUTPUT_CONTRACT
)

FIXED_LENGTH_TOKENS = 8000
NEAR_MISS_DENSITY = 0.1
DEFAULT_POSITIONS = [0.0, 0.25, 0.5, 0.75, 1.0]


def _seed_for(fact_id: str, position: float) -> int:
    digest = hashlib.sha256(f"{fact_id}:{position}".encode()).hexdigest()
    return int(digest[:8], 16)


def _position_condition_id(position: float) -> str:
    return f"position_{int(position * 100):03d}"


def _make_builder(position: float, filler_sentences: list[str], tokens_config):
    def build_user_input(case: Case) -> tuple[str, tuple]:
        clause_id = case.metadata["clause_id"]
        wrapped_fact = f"[{clause_id}] {case.metadata['fact_sentence']}"
        text = assemble_fixed_length(
            target_fact_sentence=wrapped_fact,
            filler_sentences=filler_sentences,
            near_miss_sentences=[case.metadata["near_miss_sentence"]],
            target_length_tokens=FIXED_LENGTH_TOKENS,
            relative_position=position,
            tokens_config=tokens_config,
            near_miss_density=NEAR_MISS_DENSITY,
            seed=_seed_for(case.case_id, position),
        )
        return f"{text}\n\nSoru: {case.input_text}", ()

    return build_user_input


def build_conditions(
    filler_sentences: list[str], tokens_config, positions: list[float] | None = None
) -> list[Condition]:
    positions = positions or DEFAULT_POSITIONS
    return [
        Condition(
            _position_condition_id(position),
            lambda: _COMPONENTS,
            build_user_input=_make_builder(position, filler_sentences, tokens_config),
        )
        for position in positions
    ]


def condition_order(positions: list[float] | None = None) -> list[str]:
    positions = positions or DEFAULT_POSITIONS
    return [_position_condition_id(position) for position in positions]


BASELINE_CONDITION_ID = _position_condition_id(DEFAULT_POSITIONS[0])
