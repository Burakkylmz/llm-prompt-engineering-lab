from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab_core.cli import main

SYNTHETIC_RECORDING = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "recordings"
    / "lab05"
    / "synthetic-test-recording-001"
)


def _write_results_dir_override(tmp_path: Path, extra: str = ""):
    override = tmp_path / "override.toml"
    results_dir = tmp_path / "results"
    override.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n{extra}', encoding="utf-8"
    )
    return override, results_dir


def test_fixture_run_shows_degradation_curve(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab05", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])

    captured = capsys.readouterr()
    assert "SIMULATED" in captured.out

    run_dir = next((results_dir / "lab05").iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert len(summary["per_condition"]) == 5

    acc_short = summary["per_condition"]["length_1000"]["accuracy"]
    acc_long = summary["per_condition"]["length_32000"]["accuracy"]
    assert acc_short == 1.0
    assert acc_long == 0.0
    assert (run_dir / "charts" / "accuracy_vs_length.png").exists()


def test_lengths_exceeding_preflight_limit_are_skipped_not_failed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    override, results_dir = _write_results_dir_override(
        tmp_path, extra="[preflight]\nmax_input_tokens_per_request = 5000\n"
    )
    main(["lab05", "--config", str(override), "--profile", "classroom", "--max-cases", "5"])

    captured = capsys.readouterr()
    assert "skipped lengths" in captured.out

    run_dir = next((results_dir / "lab05").iterdir())
    observations = [
        json.loads(line)
        for line in (run_dir / "observations.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    ]
    skipped = [o for o in observations if o["skip_reason"] is not None]
    errored = [o for o in observations if o["error"] is not None]
    assert len(skipped) > 0
    assert len(errored) == 0
    skipped_condition_ids = {o["condition_id"] for o in skipped}
    assert skipped_condition_ids <= {"length_8000", "length_16000", "length_32000"}


def test_replay_of_synthetic_recording(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert SYNTHETIC_RECORDING.exists()
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab05", "--config", str(override), "--replay", str(SYNTHETIC_RECORDING)])

    captured = capsys.readouterr()
    assert "Replay run written to" in captured.out
    run_dir = next((results_dir / "lab05").iterdir())
    run_metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_metadata["execution_mode"] == "replay"


def test_validate_data_includes_lab05(capsys: pytest.CaptureFixture[str]):
    main(["validate-data"])
    captured = capsys.readouterr()
    assert "lab05: OK" in captured.out
