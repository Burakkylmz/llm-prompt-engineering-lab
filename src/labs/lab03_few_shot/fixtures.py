"""Lab 03's fixture-mode resolver: deterministically echoes the gold label in the required
format. Fixture mode here tests only that the pipeline measures accuracy/tokens correctly
across conditions with different numbers/kinds of examples — it cannot and does not claim
anything about whether more or better examples actually help a real model."""

from __future__ import annotations

from lab_core.experiment_runner import Case
from lab_core.fake_client import Resolver
from lab_core.groq_client import CompletionRequest


def make_fixture_resolver(cases: list[Case]) -> Resolver:
    expected_by_text = {case.input_text: case.expected for case in cases}

    def resolve(request: CompletionRequest) -> str:
        user_text = request.messages[-1].content
        expected = expected_by_text.get(user_text)
        if expected is None:
            return "ETIKET: cold"
        return f"ETIKET: {expected['label']}"

    return resolve
