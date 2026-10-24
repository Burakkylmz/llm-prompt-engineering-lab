from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab_core.cli import main


def _write_results_dir_override(tmp_path: Path):
    override = tmp_path / "override.toml"
    results_dir = tmp_path / "results"
    override.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n', encoding="utf-8"
    )
    return override, results_dir


def test_fixture_run_produces_full_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab02", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])

    captured = capsys.readouterr()
    assert "SIMULATED" in captured.out

    run_dir = next((results_dir / "lab02").iterdir())
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "comparison.md").exists()
    assert (run_dir / "charts" / "accuracy_by_condition.png").exists()
    assert (run_dir / "charts" / "attack_success.png").exists()

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert len(summary["per_condition"]) == 8


def test_fixture_run_observation_count_matches_all_condition_groups(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(
        [
            "lab02",
            "--config",
            str(override),
            "--profile",
            "classroom",
            "--max-cases",
            "10",
            "--repetitions",
            "1",
        ]
    )
    run_dir = next((results_dir / "lab02").iterdir())
    lines = (run_dir / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 8 * 10 * 1  # 8 condition_ids x 10 cases x 1 repetition


def test_enforced_condition_shows_lower_system_level_attack_success_than_naive(tmp_path: Path):
    """The pedagogical core of Lab 02: condition C's system-level attack success must be
    lower than A's/B's, even though the raw (fixture) model behaves identically everywhere."""
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab02", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])
    run_dir = next((results_dir / "lab02").iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))

    a_system = summary["per_condition"]["A_naive_concat"]["constraint_adherence"][
        "system_level_attack_success"
    ]["rate"]
    c_system = summary["per_condition"]["C_enforced"]["constraint_adherence"][
        "system_level_attack_success"
    ]["rate"]
    c_model = summary["per_condition"]["C_enforced"]["constraint_adherence"][
        "model_level_attack_success"
    ]["rate"]

    assert c_system < a_system
    assert (
        c_model
        == summary["per_condition"]["A_naive_concat"]["constraint_adherence"][
            "model_level_attack_success"
        ]["rate"]
    )


def test_validate_data_includes_lab02(capsys: pytest.CaptureFixture[str]):
    main(["validate-data"])
    captured = capsys.readouterr()
    assert "lab02: OK" in captured.out


SYNTHETIC_RECORDING = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "recordings"
    / "lab02"
    / "synthetic-test-recording-001"
)


def test_replay_of_synthetic_recording(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert SYNTHETIC_RECORDING.exists()
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab02", "--config", str(override), "--replay", str(SYNTHETIC_RECORDING)])

    captured = capsys.readouterr()
    assert "Replay run written to" in captured.out

    run_dir = next((results_dir / "lab02").iterdir())
    run_metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_metadata["execution_mode"] == "replay"

    original = json.loads((SYNTHETIC_RECORDING / "run.json").read_text(encoding="utf-8"))
    assert original["execution_mode"] == "synthetic_recording_for_tests"
