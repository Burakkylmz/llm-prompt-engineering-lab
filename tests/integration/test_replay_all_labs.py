"""Cross-lab replay check: every shipped synthetic recording must replay *completely* —
every recorded item re-evaluated, none excluded as prompt drift.

The per-lab replay tests only asserted the new run's execution mode, which let a core bug
through (replay ignored `Condition.build_user_input`, so Labs 02/04/05/06 silently dropped
recorded items as drift). This test asserts on the observations themselves.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lab_core.cli import main

RECORDINGS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "recordings"
LABS_WITH_RECORDINGS = sorted(p.name for p in RECORDINGS.iterdir() if p.is_dir())


def test_every_lab_has_a_synthetic_recording():
    assert LABS_WITH_RECORDINGS == [f"lab0{i}" for i in range(1, 9)]


@pytest.mark.parametrize("lab_id", LABS_WITH_RECORDINGS)
def test_synthetic_recording_replays_without_drift(
    lab_id: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    recording = RECORDINGS / lab_id / "synthetic-test-recording-001"
    recorded_lines = (
        (recording / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )

    results_dir = tmp_path / "results"
    override = tmp_path / "override.toml"
    override.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n', encoding="utf-8"
    )
    # --max-cases large enough that the case subset never hides recorded items.
    main([lab_id, "--config", str(override), "--replay", str(recording), "--max-cases", "1000"])

    out = capsys.readouterr().out
    assert "prompt drift" not in out
    run_dir = next((results_dir / lab_id).iterdir())
    replayed_lines = (
        (run_dir / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )
    assert len(replayed_lines) == len(recorded_lines)
