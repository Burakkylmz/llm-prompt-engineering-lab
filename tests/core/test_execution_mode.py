from __future__ import annotations

from lab_core.execution_mode import ExecutionMode


def test_fixture_is_not_evidence_of_model_behavior():
    assert ExecutionMode.FIXTURE.is_evidence_of_model_behavior is False
    assert "SIMULATED" in ExecutionMode.FIXTURE.banner


def test_replay_and_live_are_evidence_of_model_behavior():
    assert ExecutionMode.REPLAY.is_evidence_of_model_behavior is True
    assert ExecutionMode.LIVE.is_evidence_of_model_behavior is True
    assert "SIMULATED" not in ExecutionMode.REPLAY.banner
    assert "SIMULATED" not in ExecutionMode.LIVE.banner


def test_synthetic_recording_is_not_evidence_and_is_watermarked():
    mode = ExecutionMode.SYNTHETIC_RECORDING_FOR_TESTS
    assert mode.is_evidence_of_model_behavior is False
    assert "SIMULATED" in mode.banner
