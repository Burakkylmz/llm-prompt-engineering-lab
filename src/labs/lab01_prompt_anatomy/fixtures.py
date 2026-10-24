"""The fixture-mode resolver for Lab 01 (spec Section 5): a deterministic rule, not a
fixture file, since the rule itself ("echo the gold label, strictly formatted only when the
active condition's prompt actually asked for strict formatting") is simple, exhaustively
testable, and transparent about what it is testing: the pipeline's ability to measure format
compliance correctly, not any claim about real model behavior.
"""

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
            return "ETIKET: general_inquiry\nONCELIK: low"

        label, priority = expected["label"], expected["priority"]
        system_text = request.messages[0].content
        has_output_contract = "ETIKET:" in system_text
        if has_output_contract:
            return f"ETIKET: {label}\nONCELIK: {priority}"
        return f"Bu mesaj sanirim {label} ile ilgili olabilir."

    return resolve
