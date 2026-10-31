"""The extraction-target JSON Schema, kept within the verified strict-mode feature limits
recorded in docs/groq-capabilities.md (2026-10-24): every property listed in `required`;
optional fields modeled as a `["type", "null"]` union, still required; `additionalProperties:
false` on every object, including the nested one; only the keywords/types Groq's docs
explicitly confirm (string/number/boolean/object/array/enum) — no `pattern`, `minLength`,
`format`, or conditional schemas, since those are not confirmed supported in strict mode.
"""

from __future__ import annotations

REQUEST_TYPES = ["iade", "degisim", "bilgi_talebi", "sikayet", "iptal"]
URGENCY_LEVELS = ["dusuk", "orta", "yuksek"]

EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "customer_reference": {"type": "string"},
        "request_type": {"type": "string", "enum": REQUEST_TYPES},
        "amount": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"]},
        "product": {"type": ["string", "null"]},
        "urgency": {"type": ["string", "null"]},
        "contact_info": {
            "type": "object",
            "properties": {
                "email": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
            },
            "required": ["email", "phone"],
            "additionalProperties": False,
        },
    },
    "required": [
        "customer_reference",
        "request_type",
        "amount",
        "currency",
        "product",
        "urgency",
        "contact_info",
    ],
    "additionalProperties": False,
}


def response_format_for(mode: str) -> dict | None:
    """mode is one of: plain_nl | prompt_only_json | json_object_mode |
    json_schema_best_effort | json_schema_strict."""
    if mode in ("plain_nl", "prompt_only_json"):
        return None
    if mode == "json_object_mode":
        return {"type": "json_object"}
    if mode == "json_schema_best_effort":
        return {
            "type": "json_schema",
            "json_schema": {"name": "extraction", "schema": EXTRACTION_SCHEMA, "strict": False},
        }
    if mode == "json_schema_strict":
        return {
            "type": "json_schema",
            "json_schema": {"name": "extraction", "schema": EXTRACTION_SCHEMA, "strict": True},
        }
    raise ValueError(f"Unknown mode: {mode!r}")
