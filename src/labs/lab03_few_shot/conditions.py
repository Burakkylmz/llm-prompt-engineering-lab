"""Lab 03's 11 conditions: a count series (0/2/4/8 examples, one fixed selection strategy)
and a quality series (fixed k=4, varying selection strategy) — spec Section 11 LAB 03.

Every condition shares the identical instruction/context/constraints/output_contract; only
`examples` differs, which is the controlled-variable guarantee this lab's tests assert.
"""

from __future__ import annotations

from lab_core.experiment_runner import Case, Condition
from lab_core.prompt_builder import ContextBlock, PromptComponents
from labs.lab03_few_shot.selectors import (
    select_boundary_focused,
    select_diverse_boundary,
    select_diverse_typical,
    select_misleading,
    select_random,
    select_redundant,
)

INSTRUCTION = "Gelen B2B potansiyel musteri (lead) mesajini siniflandir."

LABEL_CONTEXT = ContextBlock(
    label="Etiket Tanimlari",
    text=(
        "Kaya Elektronik B2B satis ekibi gelen talepleri su bes kategoriden birine ayirir:\n"
        "- hot: somut siparis niyeti, butce ve/veya zaman cizelgesi belirtilmis.\n"
        "- warm: ilgi var ama butce/zaman cizelgesi henuz kesin degil.\n"
        "- cold: genel bilgi talebi, somut bir plan veya niyet yok.\n"
        "- not_a_lead: satin alma ile ilgisi olmayan talep (is basvurusu, destek talebi, vb.).\n"
        "- partner_inquiry: bayilik/distributorluk/is ortakligi talebi (dogrudan siparis degil)."
    ),
)

CONSTRAINTS = (
    "Sadece asagidaki kapali etiket setinden BIR etiket sec: hot, warm, cold, not_a_lead, "
    "partner_inquiry. Cevabinda etiket disinda baska metin kullanma."
)

OUTPUT_CONTRACT = "Cevabini TAM OLARAK su formatta ver: 'ETIKET: <etiket>'"

_COMPONENTS_BASE = {
    "instruction": INSTRUCTION,
    "context": (LABEL_CONTEXT,),
    "constraints": CONSTRAINTS,
    "output_contract": OUTPUT_CONTRACT,
}


def _components_with_examples(examples: tuple) -> PromptComponents:
    return PromptComponents(**_COMPONENTS_BASE, examples=examples)


# Optional order-effect series (spec: "same 4 examples, different orders"). The reference is
# the boundary-focused k=4 condition, so only the *order* of an identical example set varies.
ORDER_REFERENCE_CONDITION_ID = "quality_boundary_focused"
ORDER_CONDITION_ORDER = ["order_boundary_reversed", "order_boundary_permuted"]
# A fixed permutation of 4 positions that is neither the identity nor the reversal, so each
# order condition is a genuinely different arrangement (asserted in tests).
_PERMUTATION_K4 = (2, 0, 3, 1)


def reorder_examples(examples: tuple, permutation: tuple[int, ...]) -> tuple:
    if sorted(permutation) != list(range(len(examples))):
        raise ValueError("permutation must reorder every example exactly once")
    return tuple(examples[i] for i in permutation)


def build_conditions(pool: list[Case], include_order_effect: bool = False) -> list[Condition]:
    count_0 = _components_with_examples(select_diverse_boundary(pool, 0))
    count_2 = _components_with_examples(select_diverse_boundary(pool, 2))
    count_4 = _components_with_examples(select_diverse_boundary(pool, 4))
    count_8 = _components_with_examples(select_diverse_boundary(pool, 8))

    quality_random_seed1 = _components_with_examples(select_random(pool, 4, seed=1))
    quality_random_seed2 = _components_with_examples(select_random(pool, 4, seed=2))
    quality_random_seed3 = _components_with_examples(select_random(pool, 4, seed=3))
    quality_redundant = _components_with_examples(select_redundant(pool, 4))
    quality_diverse_typical = _components_with_examples(select_diverse_typical(pool, 4))
    quality_boundary_focused = _components_with_examples(select_boundary_focused(pool, 4))
    quality_misleading = _components_with_examples(select_misleading(pool, 4))

    conditions = [
        Condition("count_0", lambda: count_0),
        Condition("count_2", lambda: count_2),
        Condition("count_4", lambda: count_4),
        Condition("count_8", lambda: count_8),
        Condition("quality_random_seed1", lambda: quality_random_seed1),
        Condition("quality_random_seed2", lambda: quality_random_seed2),
        Condition("quality_random_seed3", lambda: quality_random_seed3),
        Condition("quality_redundant", lambda: quality_redundant),
        Condition("quality_diverse_typical", lambda: quality_diverse_typical),
        Condition("quality_boundary_focused", lambda: quality_boundary_focused),
        Condition("quality_misleading", lambda: quality_misleading),
    ]
    if include_order_effect:
        boundary_examples = quality_boundary_focused.examples
        reversed_components = _components_with_examples(tuple(reversed(boundary_examples)))
        permuted_components = _components_with_examples(
            reorder_examples(boundary_examples, _PERMUTATION_K4)
        )
        conditions.append(Condition("order_boundary_reversed", lambda: reversed_components))
        conditions.append(Condition("order_boundary_permuted", lambda: permuted_components))
    return conditions


CONDITION_ORDER = [
    "count_0",
    "count_2",
    "count_4",
    "count_8",
    "quality_random_seed1",
    "quality_random_seed2",
    "quality_random_seed3",
    "quality_redundant",
    "quality_diverse_typical",
    "quality_boundary_focused",
    "quality_misleading",
]
BASELINE_CONDITION_ID = "count_0"
