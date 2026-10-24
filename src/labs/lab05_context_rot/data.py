"""Loads and validates Lab 05's target facts + shared filler pool (spec Section 9.2: >=20
distinct target facts; distractor corpus large enough to reach the largest configured
length without repeating identical filler text)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lab_core.datasets import DatasetError, load_json, validate_against_schema
from lab_core.experiment_runner import Case

FACTS_DIR = Path(__file__).resolve().parents[3] / "data" / "golden" / "lab05"
FILLER_DIR = Path(__file__).resolve().parents[3] / "data" / "contexts" / "lab05"

MIN_FACTS = 20


@dataclass(frozen=True)
class Fact:
    fact_id: str
    fact_type: str
    fact_sentence: str
    near_miss_sentence: str
    question: str
    gold_answer: str
    near_miss_answer: str


def load_facts() -> tuple[list[Fact], dict]:
    payload = load_json(FACTS_DIR / "facts.json")
    validate_against_schema(payload, "lab05_facts.schema.json")
    if len(payload["facts"]) < MIN_FACTS:
        raise DatasetError(f"Lab05 has {len(payload['facts'])} facts, minimum is {MIN_FACTS}")
    facts = [
        Fact(
            fact_id=f["fact_id"],
            fact_type=f["fact_type"],
            fact_sentence=f["fact_sentence"],
            near_miss_sentence=f["near_miss_sentence"],
            question=f["question"],
            gold_answer=f["gold_answer"],
            near_miss_answer=f["near_miss_answer"],
        )
        for f in payload["facts"]
    ]
    return facts, payload


def facts_to_cases(facts: list[Fact]) -> list[Case]:
    return [
        Case(
            case_id=fact.fact_id,
            input_text=fact.question,
            expected={"gold_answer": fact.gold_answer, "near_miss_answer": fact.near_miss_answer},
            metadata={
                "fact_sentence": fact.fact_sentence,
                "near_miss_sentence": fact.near_miss_sentence,
                "fact_type": fact.fact_type,
            },
        )
        for fact in facts
    ]


def load_filler(max_length_tokens: int, tokens_config) -> tuple[list[str], list[str], dict]:
    from lab_core.tokens import estimate_tokens

    payload = load_json(FILLER_DIR / "filler.json")
    validate_against_schema(payload, "lab05_filler.schema.json")

    total_tokens = sum(estimate_tokens(s, tokens_config) for s in payload["filler_sentences"])
    if total_tokens < max_length_tokens:
        raise DatasetError(
            f"Lab05 filler pool has ~{total_tokens} estimated tokens, which is less than "
            f"the largest configured context length ({max_length_tokens}); it cannot reach "
            "that length without repeating identical filler text"
        )
    return payload["filler_sentences"], payload["generic_near_miss_noise"], payload
