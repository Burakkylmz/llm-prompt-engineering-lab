"""Lab 04's 9 conditions (spec Section 11 LAB 04): all-documents, relevance-filtered,
+dedup, +dedup+freshness, a budget series, and an ordering series over the fixed
relevance+dedup+freshness set.

The system prompt (instruction/constraints/output contract) is identical across every
condition; only *which documents get rendered into the user message, and in what order* -
differs, via `Condition.build_user_input`.
"""

from __future__ import annotations

from lab_core.context_manager import Document
from lab_core.experiment_runner import Case, Condition
from lab_core.prompt_builder import PromptComponents
from labs.lab04_context_selection.selection import (
    select_all_documents,
    select_ordered_variant,
    select_relevance_budget,
    select_relevance_dedup_fresh_top_k,
    select_relevance_dedup_top_k,
    select_relevance_top_k,
)

INSTRUCTION = "Asagidaki sirket politika belgelerine dayanarak soruyu cevapla."

CONSTRAINTS = (
    "Sadece verilen belgelerdeki bilgiyi kullan. Belgelerde cevap yoksa 'bulunamadi' yaz. "
    "Kullandigin belgenin ID'sini belirt."
)

OUTPUT_CONTRACT = (
    "Cevabini TAM OLARAK su formatta ver: 'CEVAP: <cevap> | KAYNAK: <belge_id>' "
    "(belge bulunamadiysa: 'CEVAP: bulunamadi | KAYNAK: yok')"
)

_COMPONENTS = PromptComponents(
    instruction=INSTRUCTION, constraints=CONSTRAINTS, output_contract=OUTPUT_CONTRACT
)

BUDGET_TOKENS = {"budget_200": 200, "budget_500": 500, "budget_1000": 1000}
ALL_DOCUMENTS_CAP_TOKENS = 8000

CONDITION_ORDER = [
    "all_documents",
    "relevance_top5",
    "relevance_dedup_top5",
    "relevance_dedup_fresh_top5",
    "budget_200",
    "budget_500",
    "budget_1000",
    "order_relevance_asc",
    "order_seeded_random",
]
BASELINE_CONDITION_ID = "all_documents"


def render_documents(docs: list[Document]) -> str:
    if not docs:
        return "(Hicbir belge saglanmadi.)"
    return "\n\n".join(f"[BELGE_ID: {doc.doc_id}]\n{doc.text}" for doc in docs)


def build_selector_functions(corpus: list[Document], tokens_config) -> dict:
    """One selector per condition_id: `question_text -> list[Document]`. Shared between
    prompt-building (`build_conditions`) and the selection-level (no-LLM) metrics computed
    directly in `cli.py` — one implementation, not two."""
    return {
        "all_documents": lambda q: select_all_documents(
            q, corpus, tokens_config, ALL_DOCUMENTS_CAP_TOKENS
        ),
        "relevance_top5": lambda q: select_relevance_top_k(q, corpus),
        "relevance_dedup_top5": lambda q: select_relevance_dedup_top_k(q, corpus),
        "relevance_dedup_fresh_top5": lambda q: select_relevance_dedup_fresh_top_k(q, corpus),
        "budget_200": lambda q: select_relevance_budget(
            q, corpus, BUDGET_TOKENS["budget_200"], tokens_config
        ),
        "budget_500": lambda q: select_relevance_budget(
            q, corpus, BUDGET_TOKENS["budget_500"], tokens_config
        ),
        "budget_1000": lambda q: select_relevance_budget(
            q, corpus, BUDGET_TOKENS["budget_1000"], tokens_config
        ),
        "order_relevance_asc": lambda q: select_ordered_variant(q, corpus, "relevance_asc"),
        "order_seeded_random": lambda q: select_ordered_variant(
            q, corpus, "seeded_random", seed=20261024
        ),
    }


def _make_builder(select_fn):
    def build_user_input(case: Case) -> tuple[str, tuple]:
        question = case.input_text
        docs = select_fn(question)
        return f"{render_documents(docs)}\n\nSoru: {question}", ()

    return build_user_input


def build_conditions(corpus: list[Document], tokens_config) -> list[Condition]:
    selectors = build_selector_functions(corpus, tokens_config)
    return [
        Condition(
            condition_id,
            lambda: _COMPONENTS,
            build_user_input=_make_builder(selectors[condition_id]),
        )
        for condition_id in CONDITION_ORDER
    ]
