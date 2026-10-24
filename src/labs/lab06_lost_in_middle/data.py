"""Lab 06 shares Lab 05's target-fact and filler pool (spec Section 11 LAB 06: "may share
the Lab 05 pool, but runs separately") — same facts, same filler sentences, but each fact's
sentence is wrapped with a stable clause ID so the evidence-identification metric ("the
model reports the clause ID it used") has something concrete to check.
"""

from __future__ import annotations

from lab_core.experiment_runner import Case
from labs.lab05_context_rot.data import Fact, load_facts, load_filler  # noqa: F401  (re-exported)

MIN_FACTS = 20


def clause_id_for(index: int) -> str:
    return f"MADDE-{index + 1:02d}"


def facts_to_cases_with_clause_ids(facts: list[Fact]) -> list[Case]:
    return [
        Case(
            case_id=fact.fact_id,
            input_text=fact.question,
            expected={"gold_answer": fact.gold_answer, "near_miss_answer": fact.near_miss_answer},
            metadata={
                "fact_sentence": fact.fact_sentence,
                "near_miss_sentence": fact.near_miss_sentence,
                "fact_type": fact.fact_type,
                "clause_id": clause_id_for(index),
            },
        )
        for index, fact in enumerate(facts)
    ]
