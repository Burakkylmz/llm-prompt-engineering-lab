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
    / "lab03"
    / "synthetic-test-recording-001"
)


def _write_results_dir_override(tmp_path: Path):
    override = tmp_path / "override.toml"
    results_dir = tmp_path / "results"
    override.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n', encoding="utf-8"
    )
    return override, results_dir


def test_fixture_run_produces_full_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab03", "--config", str(override), "--profile", "classroom", "--max-cases", "20"])

    captured = capsys.readouterr()
    assert "SIMULATED" in captured.out

    run_dir = next((results_dir / "lab03").iterdir())
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "charts" / "quality_vs_tokens.png").exists()

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert len(summary["per_condition"]) == 11


def test_observation_count_matches_full_paired_cross_product(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(
        [
            "lab03",
            "--config",
            str(override),
            "--profile",
            "classroom",
            "--max-cases",
            "20",
            "--repetitions",
            "1",
        ]
    )
    run_dir = next((results_dir / "lab03").iterdir())
    lines = (run_dir / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 11 * 20 * 1


def test_paired_design_same_cases_across_all_conditions(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab03", "--config", str(override), "--profile", "classroom", "--max-cases", "20"])
    run_dir = next((results_dir / "lab03").iterdir())
    observations = [
        json.loads(line)
        for line in (run_dir / "observations.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    ]
    cases_per_condition: dict[str, set[str]] = {}
    for obs in observations:
        cases_per_condition.setdefault(obs["condition_id"], set()).add(obs["case_id"])
    distinct_sets = {frozenset(v) for v in cases_per_condition.values()}
    assert len(distinct_sets) == 1  # every condition ran on the identical case set


def test_token_counts_increase_with_example_count(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab03", "--config", str(override), "--profile", "classroom", "--max-cases", "20"])
    run_dir = next((results_dir / "lab03").iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    tokens_0 = summary["per_condition"]["count_0"]["mean_prompt_tokens"]
    tokens_8 = summary["per_condition"]["count_8"]["mean_prompt_tokens"]
    assert tokens_8 > tokens_0


def test_replay_of_synthetic_recording(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert SYNTHETIC_RECORDING.exists()
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab03", "--config", str(override), "--replay", str(SYNTHETIC_RECORDING)])

    captured = capsys.readouterr()
    assert "Replay run written to" in captured.out
    run_dir = next((results_dir / "lab03").iterdir())
    run_metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_metadata["execution_mode"] == "replay"


def test_validate_data_includes_lab03(capsys: pytest.CaptureFixture[str]):
    main(["validate-data"])
    captured = capsys.readouterr()
    assert "lab03: OK" in captured.out
