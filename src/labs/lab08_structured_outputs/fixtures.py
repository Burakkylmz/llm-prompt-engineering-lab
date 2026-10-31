"""Lab 08's fixture-mode resolver: `plain_nl` gets a free-text (non-JSON) response — this
is the condition explicitly meant to show the parse-success "gap" — every other condition
gets a valid JSON string matching the gold extraction. Fixture mode cannot simulate the
*real* difference between JSON Object Mode / best-effort / strict schema modes (that
difference only exists in how a real model's decoding is constrained), so those three are
deliberately identical here; only `plain_nl` is meant to look different.
"""

from __future__ import annotations

import json

from lab_core.experiment_runner import Case
from lab_core.fake_client import Resolver
from lab_core.groq_client import CompletionRequest

_JSON_MARKER = "SADECE gecerli bir JSON"


def make_fixture_resolver(cases: list[Case]) -> Resolver:
    gold_by_text = {case.input_text: case.expected for case in cases}

    def resolve(request: CompletionRequest) -> str:
        system_text = request.messages[0].content
        user_text = request.messages[-1].content

        gold = gold_by_text.get(user_text)
        if gold is None:
            return "Musteriye iliskin bilgi bulunamadi."

        if _JSON_MARKER not in system_text:
            return f"Musterinin talebi su sekilde ozetlenebilir: {gold['request_type']} talebi."

        return json.dumps(gold, ensure_ascii=False)

    return resolve
