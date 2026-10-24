"""The single execution-mode enum that flows through every layer of the pipeline.

Every observation, report, and chart carries one of these three values explicitly
(spec Section 5) — no layer infers the mode from an implementation detail such as
"is the injected client a FakeGroqClient".
"""

from __future__ import annotations

from enum import StrEnum


class ExecutionMode(StrEnum):
    FIXTURE = "fixture"
    REPLAY = "replay"
    LIVE = "live"
    SYNTHETIC_RECORDING_FOR_TESTS = "synthetic_recording_for_tests"

    @property
    def is_evidence_of_model_behavior(self) -> bool:
        """fixture is a pipeline test only; replay/live reflect a real model call."""
        return self in (ExecutionMode.REPLAY, ExecutionMode.LIVE)

    @property
    def banner(self) -> str:
        if self is ExecutionMode.FIXTURE:
            return "SIMULATED — fixture responses, not model output"
        if self is ExecutionMode.SYNTHETIC_RECORDING_FOR_TESTS:
            return "SIMULATED — synthetic recording, test fixture only"
        if self is ExecutionMode.REPLAY:
            return "REPLAY — real model responses recorded in a prior live run"
        return "LIVE — real-time Groq API responses"
