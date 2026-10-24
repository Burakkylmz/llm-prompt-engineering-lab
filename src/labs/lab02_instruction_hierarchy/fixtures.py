"""Lab 02's fixture-mode resolver.

Deliberately simulates a **maximally vulnerable** fake assistant: it complies with any
embedded override attempt (detected via the literal "ONAYLA" instruction every injection/
override fixture contains) and discloses the canary token whenever asked to, regardless of
whether the active condition wrapped the untrusted content safely. This is what makes the
condition comparison show a non-trivial "model-level attack success" even in fixture mode —
it exercises the measurement pipeline (can it detect a 100%-vulnerable model's compliance and
later, under the enforced evaluator, show the application blocking it?) without claiming
anything about how a real model actually behaves. Every fixture-mode report is watermarked
SIMULATED; see the lab README for why this specific behavior was chosen over "always safe."
"""

from __future__ import annotations

from lab_core.experiment_runner import Case
from lab_core.fake_client import Resolver
from lab_core.groq_client import CompletionRequest
from labs.lab02_instruction_hierarchy.policy import CANARY_TOKEN

_OVERRIDE_MARKER = "ONAYLA"


def make_fixture_resolver(all_cases: list[Case]) -> Resolver:
    by_prefix = sorted(((case.input_text, case) for case in all_cases), key=lambda t: -len(t[0]))

    def resolve(request: CompletionRequest) -> str:
        user_text = request.messages[-1].content
        matched = next((case for prefix, case in by_prefix if user_text.startswith(prefix)), None)
        if matched is None:
            return "ETIKET: escalate"

        gold = matched.expected["gold_decision"]
        attack_goal = matched.expected["attack_goal"]

        if _OVERRIDE_MARKER in user_text:
            return "ETIKET: approve"
        if attack_goal == "leak_canary":
            return f"Debug cikisi: {CANARY_TOKEN}\nETIKET: {gold}"
        return f"ETIKET: {gold}"

    return resolve
