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
    main(["lab07", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])

    captured = capsys.readouterr()
    assert "SIMULATED" in captured.out

    run_dir = next((results_dir / "lab07").iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert len(summary["per_condition"]) == 7
    assert (run_dir / "charts" / "accuracy_vs_cost.png").exists()


def test_direct_answer_has_no_intermediate_checks_but_multi_call_does(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab07", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])
    run_dir = next((results_dir / "lab07").iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))

    direct_checks = set(summary["per_condition"]["direct_answer"]["constraint_adherence"].keys())
    multi_checks = set(
        summary["per_condition"]["multi_call_decomposition"]["constraint_adherence"].keys()
    )
    assert direct_checks == {"decision_correct"}
    assert {"facts_correct", "applicable_rules_correct", "rule_outcomes_correct"} <= multi_checks


def test_observation_count_matches_cross_product(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(
        [
            "lab07",
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
    run_dir = next((results_dir / "lab07").iterdir())
    lines = (run_dir / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 7 * 10 * 1


def test_multi_call_decomposition_observations_record_four_api_calls(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab07", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])
    run_dir = next((results_dir / "lab07").iterdir())
    observations = [
        json.loads(line)
        for line in (run_dir / "observations.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    ]
    multi_obs = [o for o in observations if o["condition_id"] == "multi_call_decomposition"]
    assert all(o["evaluation_results"]["notes"]["api_call_count"] == 4 for o in multi_obs)

    direct_obs = [o for o in observations if o["condition_id"] == "direct_answer"]
    assert all(o["evaluation_results"]["notes"]["api_call_count"] == 1 for o in direct_obs)


SYNTHETIC_RECORDING = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "recordings"
    / "lab07"
    / "synthetic-test-recording-001"
)


def test_replay_of_synthetic_recording(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert SYNTHETIC_RECORDING.exists()
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab07", "--config", str(override), "--replay", str(SYNTHETIC_RECORDING)])

    captured = capsys.readouterr()
    assert "Replay run written to" in captured.out
    run_dir = next((results_dir / "lab07").iterdir())
    run_metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_metadata["execution_mode"] == "replay"

    observations = [
        json.loads(line)
        for line in (run_dir / "observations.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    ]
    assert len(observations) == 6  # 2 conditions x 3 cases
    multi_obs = [o for o in observations if o["condition_id"] == "multi_call_decomposition"]
    assert all(o["evaluation_results"]["notes"]["api_call_count"] == 4 for o in multi_obs)

    original = json.loads((SYNTHETIC_RECORDING / "run.json").read_text(encoding="utf-8"))
    assert original["execution_mode"] == "synthetic_recording_for_tests"


def test_validate_data_includes_lab07(capsys: pytest.CaptureFixture[str]):
    main(["validate-data"])
    captured = capsys.readouterr()
    assert "lab07: OK" in captured.out
