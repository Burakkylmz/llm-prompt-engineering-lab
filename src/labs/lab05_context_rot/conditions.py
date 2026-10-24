"""Lab 05's length-series conditions (spec Section 11 LAB 05): the same target fact's
relative position (fixed at 50%) and the same near-miss density, varying only the total
context length. Built on `lab_core.context_manager.assemble_fixed_length`.
"""

from __future__ import annotations

import hashlib

from lab_core.context_manager import assemble_fixed_length
from lab_core.experiment_runner import Case, Condition
from lab_core.prompt_builder import PromptComponents

INSTRUCTION = "Asagidaki metinde gecen bilgiye dayanarak soruyu cevapla."
CONSTRAINTS = "Sadece metinde acikca belirtilen bilgiyi kullan. Cevap metinde yoksa tahmin etme."
OUTPUT_CONTRACT = (
    "Cevabini TAM OLARAK su formatta ver: 'CEVAP: <deger>' "
    "(metinde bulunamiyorsa: 'CEVAP: BULUNAMADI')"
)
_COMPONENTS = PromptComponents(
    instruction=INSTRUCTION, constraints=CONSTRAINTS, output_contract=OUTPUT_CONTRACT
)

RELATIVE_POSITION = 0.5
NEAR_MISS_DENSITY = 0.1

DEFAULT_LENGTHS_TOKENS = [1000, 4000, 8000, 16000, 32000]


def _seed_for(fact_id: str, length_tokens: int) -> int:
    digest = hashlib.sha256(f"{fact_id}:{length_tokens}".encode()).hexdigest()
    return int(digest[:8], 16)


def _make_builder(length_tokens: int, filler_sentences: list[str], tokens_config):
    def build_user_input(case: Case) -> tuple[str, tuple]:
        fact_sentence = case.metadata["fact_sentence"]
        near_miss_sentence = case.metadata["near_miss_sentence"]
        text = assemble_fixed_length(
            target_fact_sentence=fact_sentence,
            filler_sentences=filler_sentences,
            near_miss_sentences=[near_miss_sentence],
            target_length_tokens=length_tokens,
            relative_position=RELATIVE_POSITION,
            tokens_config=tokens_config,
            near_miss_density=NEAR_MISS_DENSITY,
            seed=_seed_for(case.case_id, length_tokens),
        )
        return f"{text}\n\nSoru: {case.input_text}", ()

    return build_user_input


def build_conditions(
    filler_sentences: list[str], tokens_config, lengths: list[int] | None = None
) -> list[Condition]:
    lengths = lengths or DEFAULT_LENGTHS_TOKENS
    return [
        Condition(
            f"length_{length}",
            lambda: _COMPONENTS,
            build_user_input=_make_builder(length, filler_sentences, tokens_config),
        )
        for length in lengths
    ]


def condition_order(lengths: list[int] | None = None) -> list[str]:
    lengths = lengths or DEFAULT_LENGTHS_TOKENS
    return [f"length_{length}" for length in lengths]


BASELINE_CONDITION_ID = f"length_{DEFAULT_LENGTHS_TOKENS[0]}"
