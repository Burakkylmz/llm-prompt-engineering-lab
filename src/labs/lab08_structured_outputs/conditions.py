"""Lab 08's 5 conditions (spec Section 11 LAB 08): identical task and field description
across every condition; only the requested output *mode* changes (no JSON request at all,
a prompt-only JSON request, provider JSON Object Mode, JSON Schema best-effort, JSON
Schema strict) via `generation_overrides["response_format"]`.
"""

from __future__ import annotations

from lab_core.experiment_runner import Condition
from lab_core.prompt_builder import PromptComponents
from labs.lab08_structured_outputs.schema import response_format_for

TASK_INSTRUCTION = "Musteri talebini oku ve asagidaki bilgileri cikar."

FIELD_DESCRIPTION = (
    "Cikarilacak alanlar: customer_reference (metin), request_type "
    "(iade|degisim|bilgi_talebi|sikayet|iptal), amount (sayi, belirtilmemisse null), "
    "currency (metin, belirtilmemisse null), product (metin, belirtilmemisse null), "
    "urgency (dusuk|orta|yuksek, belirtilmemisse null), contact_info (email ve phone "
    "alanlarini iceren nesne, biri belirtilmemisse null)."
)

JSON_OUTPUT_CONTRACT = (
    "Cevabini SADECE gecerli bir JSON nesnesi olarak ver, baska hicbir metin ekleme. "
    'Ornek yapı: {"customer_reference": "...", "request_type": "...", "amount": null, '
    '"currency": null, "product": null, "urgency": null, '
    '"contact_info": {"email": null, "phone": null}}'
)

CONDITION_ORDER = [
    "plain_nl",
    "prompt_only_json",
    "json_object_mode",
    "json_schema_best_effort",
    "json_schema_strict",
]
BASELINE_CONDITION_ID = "plain_nl"


def build_conditions() -> list[Condition]:
    plain_nl_components = PromptComponents(
        instruction=(
            f"{TASK_INSTRUCTION}\n\n{FIELD_DESCRIPTION}\n\n"
            "Cevabini normal cumlelerle aciklayarak ver."
        )
    )
    json_components = PromptComponents(
        instruction=f"{TASK_INSTRUCTION}\n\n{FIELD_DESCRIPTION}",
        output_contract=JSON_OUTPUT_CONTRACT,
    )

    return [
        Condition("plain_nl", lambda: plain_nl_components),
        Condition(
            "prompt_only_json",
            lambda: json_components,
            generation_overrides={"response_format": response_format_for("prompt_only_json")},
        ),
        Condition(
            "json_object_mode",
            lambda: json_components,
            generation_overrides={"response_format": response_format_for("json_object_mode")},
        ),
        Condition(
            "json_schema_best_effort",
            lambda: json_components,
            generation_overrides={
                "response_format": response_format_for("json_schema_best_effort")
            },
        ),
        Condition(
            "json_schema_strict",
            lambda: json_components,
            generation_overrides={"response_format": response_format_for("json_schema_strict")},
        ),
    ]
