"""Lab 01's six conditions (spec Section 11 LAB 01): cumulative instruction -> context ->
constraints -> output contract -> examples, plus a length-matched neutral-padding control.

Optional leave-one-out ablation (spec: "extended profile"): the full prompt (D) minus exactly
one component at a time. "Full prompt minus examples" is *identical* to condition C, so it is
not run twice — `ABLATION_EQUIVALENTS` records that C plays that role in the ablation table.

Every condition shares the identical `instruction` text; later conditions layer additional
components on top, never replacing earlier ones — this is what "cumulative" means here, and
is asserted by `tests/labs/test_lab01.py`.
"""

from __future__ import annotations

from dataclasses import replace

from lab_core.config import TokensConfig
from lab_core.experiment_runner import Case, Condition
from lab_core.prompt_builder import ContextBlock, Example, PromptComponents, build_messages
from lab_core.tokens import estimate_messages_tokens
from labs.lab01_prompt_anatomy.data import LABELS

INSTRUCTION = "Gelen musteri mesajini siniflandir."

BUSINESS_CONTEXT = ContextBlock(
    label="Sirket Baglami",
    text=(
        "Kaya Elektronik, tuketici elektronigi satan bir sirkettir. Musteri destek "
        "ekibi gelen mesajlari asagidaki bes kategoriden birine ayirir:\n"
        "- billing: fatura, odeme, ucretlendirme ile ilgili konular.\n"
        "- technical_issue: urun veya hizmetin calismamasi, kurulum veya baglanti sorunlari.\n"
        "- cancellation: siparis veya abonelik iptali, fesih talepleri.\n"
        "- complaint: hizmet kalitesi, teslimat, personel davranisi ile ilgili genel sikayetler "
        "(teknik ariza veya fatura hatasi DISINDAKI sikayetler).\n"
        "- general_inquiry: yukaridaki dort kategoriye girmeyen bilgi talepleri (garanti suresi, "
        "calisma saatleri, stok durumu vb.)."
    ),
)

CONSTRAINTS = (
    "Kurallar:\n"
    "1. Sadece asagidaki kapali etiket setinden BIR etiket sec: " + ", ".join(LABELS) + ".\n"
    "2. Cevabinda etiket ve oncelik disinda baska metin kullanma.\n"
    "3. Mesaj birden fazla kategoriye girebiliyorsa, musterinin ilk somut olarak belirttigi "
    "soruna gore karar ver (belirsizlik durumunda ilk bahsedilen konu kazanir)."
)

OUTPUT_CONTRACT = (
    "Cevabini TAM OLARAK su iki satirlik formatta ver, baska hicbir sey yazma:\n"
    "ETIKET: <billing|technical_issue|cancellation|complaint|general_inquiry>\n"
    "ONCELIK: <low|medium|high>"
)

_NEUTRAL_FILLER_SENTENCES = [
    "Bu bolum sirket ici egitim notlari icin eklenmistir ve siniflandirma kararini etkilemez.",
    "Kaya Elektronik, 1998 yilindan beri tuketici elektronigi alaninda faaliyet gostermektedir.",
    "Musteri destek ekibi haftanin yedi gunu, gunde oniki saat hizmet vermektedir.",
    "Bu metin, uzunluk kontrolu amaciyla eklenmis, gorevle dogrudan ilgisi olmayan dolgu metnidir.",
    "Sirket ici kalite standartlari duzenli olarak gozden gecirilmekte ve guncellenmektedir.",
]


def _select_examples(example_pool: list[Case], per_class: int = 1) -> tuple[Example, ...]:
    """Deliberately diverse selection: one typical example per class (spec's "carefully
    selected" condition D), in label order, so every class is represented."""
    examples: list[Example] = []
    seen_labels: set[str] = set()
    for label in LABELS:
        for case in example_pool:
            if case.expected["label"] == label and label not in seen_labels:
                examples.append(
                    Example(
                        input_text=case.input_text,
                        output_text=f"ETIKET: {label}\nONCELIK: {case.expected['priority']}",
                    )
                )
                seen_labels.add(label)
                break
    return tuple(examples)


def _build_padding(target_extra_tokens: int, tokens_config: TokensConfig) -> str:
    if target_extra_tokens <= 0:
        return ""
    from lab_core.tokens import estimate_tokens

    text = ""
    guard = 0
    while estimate_tokens(text, tokens_config) < target_extra_tokens and guard < 2000:
        sentence = _NEUTRAL_FILLER_SENTENCES[guard % len(_NEUTRAL_FILLER_SENTENCES)]
        text = (text + " " + sentence).strip()
        guard += 1
    return text


def build_ablation_components(full: PromptComponents) -> dict[str, PromptComponents]:
    """The full prompt minus exactly one component. Every other component is the *same
    object* as in the full prompt, which is what makes each row a single-variable change."""
    return {
        "LOO_no_instruction": replace(full, instruction=""),
        "LOO_no_context": replace(full, context=()),
        "LOO_no_constraints": replace(full, constraints=None),
        "LOO_no_output_contract": replace(full, output_contract=None),
    }


def build_conditions(
    example_pool: list[Case], tokens_config: TokensConfig, include_ablation: bool = False
) -> list[Condition]:
    sample_input = "Ornek musteri mesaji metni."
    examples = _select_examples(example_pool)

    baseline_components = PromptComponents(instruction=INSTRUCTION)
    a_components = PromptComponents(instruction=INSTRUCTION, context=(BUSINESS_CONTEXT,))
    b_components = PromptComponents(
        instruction=INSTRUCTION, context=(BUSINESS_CONTEXT,), constraints=CONSTRAINTS
    )
    c_components = PromptComponents(
        instruction=INSTRUCTION,
        context=(BUSINESS_CONTEXT,),
        constraints=CONSTRAINTS,
        output_contract=OUTPUT_CONTRACT,
    )
    d_components = PromptComponents(
        instruction=INSTRUCTION,
        context=(BUSINESS_CONTEXT,),
        constraints=CONSTRAINTS,
        output_contract=OUTPUT_CONTRACT,
        examples=examples,
    )

    b_tokens = estimate_messages_tokens(
        [m.as_dict() for m in build_messages(b_components, sample_input)], tokens_config
    )
    d_tokens = estimate_messages_tokens(
        [m.as_dict() for m in build_messages(d_components, sample_input)], tokens_config
    )
    padding = _build_padding(d_tokens - b_tokens, tokens_config)
    b_len_components = PromptComponents(
        instruction=INSTRUCTION,
        context=(BUSINESS_CONTEXT,),
        constraints=CONSTRAINTS + ("\n\n" + padding if padding else ""),
    )

    conditions = [
        Condition("baseline", lambda: baseline_components),
        Condition("A_context", lambda: a_components),
        Condition("B_constraints", lambda: b_components),
        Condition("B_len", lambda: b_len_components),
        Condition("C_output_contract", lambda: c_components),
        Condition("D_examples", lambda: d_components),
    ]
    if include_ablation:
        for condition_id, components in build_ablation_components(d_components).items():
            conditions.append(Condition(condition_id, lambda c=components: c))
    return conditions


CONDITION_ORDER = [
    "baseline",
    "A_context",
    "B_constraints",
    "B_len",
    "C_output_contract",
    "D_examples",
]
BASELINE_CONDITION_ID = "baseline"

ABLATION_REFERENCE_CONDITION_ID = "D_examples"
ABLATION_CONDITION_ORDER = [
    "LOO_no_instruction",
    "LOO_no_context",
    "LOO_no_constraints",
    "LOO_no_output_contract",
]
# component removed -> the condition that already represents "full prompt minus it"
ABLATION_EQUIVALENTS = {"LOO_no_examples": "C_output_contract"}
