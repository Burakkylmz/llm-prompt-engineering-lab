"""Lab 06's fixture-mode resolver: a deterministic "U-shaped" rule (correct near the start
or end of the context, confused by the near-miss distractor in the middle) — the classic
lost-in-the-middle shape, applied here only to exercise the measurement/reporting pipeline.
Position is inferred from where the clause tag literally sits in the rendered text (its
character-offset ratio), not from any hidden condition identifier. Not a claim about real
model behavior.
"""

from __future__ import annotations

import re

from lab_core.experiment_runner import Case
from lab_core.fake_client import Resolver
from lab_core.groq_client import CompletionRequest

_CLAUSE_RE = re.compile(r"\[(MADDE-\d+)\]")


def make_fixture_resolver(cases: list[Case]) -> Resolver:
    cases_by_clause_id = {c.metadata["clause_id"]: c for c in cases}

    def resolve(request: CompletionRequest) -> str:
        user_text = request.messages[-1].content
        match = _CLAUSE_RE.search(user_text)
        if match is None:
            return "CEVAP: BULUNAMADI | MADDE: YOK"
        clause_id = match.group(1)
        matched = cases_by_clause_id.get(clause_id)
        if matched is None:
            return "CEVAP: BULUNAMADI | MADDE: YOK"

        ratio = match.start() / max(1, len(user_text))
        if ratio <= 0.2 or ratio >= 0.8:
            return f"CEVAP: {matched.expected['gold_answer']} | MADDE: {clause_id}"
        return f"CEVAP: {matched.expected['near_miss_answer']} | MADDE: {clause_id}"

    return resolve
