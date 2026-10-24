"""Lab 04's fixture-mode resolver.

Deterministic rule tied directly to what was actually rendered into the prompt: if the
current (gold) document's ID tag is present in the context, answer correctly and cite it; if
only the stale (superseded) document's ID tag is present, answer with the stale value and
cite the stale doc (simulating a model that answers correctly *from whatever it was shown*,
right or wrong); if neither is present, report "bulunamadi". This exercises the full
selection-to-answer pipeline honestly in fixture mode: the *measured* answer quality is
entirely a function of what the (simulated) selector included, which is exactly the point
Lab 04 teaches. It is not a claim about how a real model would behave.
"""

from __future__ import annotations

from lab_core.experiment_runner import Case
from lab_core.fake_client import Resolver
from lab_core.groq_client import CompletionRequest


def make_fixture_resolver(cases: list[Case]) -> Resolver:
    by_question_suffix = sorted(
        ((f"Soru: {case.input_text}", case) for case in cases), key=lambda t: -len(t[0])
    )

    def resolve(request: CompletionRequest) -> str:
        user_text = request.messages[-1].content
        matched = next(
            (case for suffix, case in by_question_suffix if user_text.endswith(suffix)), None
        )
        if matched is None:
            return "CEVAP: bulunamadi | KAYNAK: yok"

        gold_doc_id = matched.expected["gold_evidence_doc_ids"][0]
        stale_doc_id = matched.expected.get("stale_doc_id")

        if f"[BELGE_ID: {gold_doc_id}]" in user_text:
            return f"CEVAP: {matched.expected['gold_answer']} | KAYNAK: {gold_doc_id}"
        if stale_doc_id and f"[BELGE_ID: {stale_doc_id}]" in user_text:
            return f"CEVAP: {matched.expected['stale_value']} | KAYNAK: {stale_doc_id}"
        return "CEVAP: bulunamadi | KAYNAK: yok"

    return resolve
