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
    / "lab04"
    / "synthetic-test-recording-001"
)


def _write_results_dir_override(tmp_path: Path):
    override = tmp_path / "override.toml"
    results_dir = tmp_path / "results"
    override.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n', encoding="utf-8"
    )
    return override, results_dir


def test_fixture_run_produces_full_report_with_selection_metrics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab04", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])

    captured = capsys.readouterr()
    assert "SIMULATED" in captured.out

    run_dir = next((results_dir / "lab04").iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert len(summary["per_condition"]) == 9
    assert "selection_metrics" in summary
    assert len(summary["selection_metrics"]) == 9

    comparison = (run_dir / "comparison.md").read_text(encoding="utf-8")
    assert "Selection-level metrics" in comparison
    assert (run_dir / "charts" / "budget_vs_recall_accuracy.png").exists()


def test_freshness_condition_has_lower_stale_inclusion_than_naive(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab04", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])
    run_dir = next((results_dir / "lab04").iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))

    naive_stale = summary["selection_metrics"]["relevance_top5"]["stale_inclusion_rate"][
        "point_estimate"
    ]
    fresh_stale = summary["selection_metrics"]["relevance_dedup_fresh_top5"][
        "stale_inclusion_rate"
    ]["point_estimate"]
    assert fresh_stale <= naive_stale


def test_observation_count_matches_cross_product(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(
        [
            "lab04",
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
    run_dir = next((results_dir / "lab04").iterdir())
    lines = (run_dir / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 9 * 10 * 1


def test_replay_of_synthetic_recording(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert SYNTHETIC_RECORDING.exists()
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab04", "--config", str(override), "--replay", str(SYNTHETIC_RECORDING)])

    captured = capsys.readouterr()
    assert "Replay run written to" in captured.out
    run_dir = next((results_dir / "lab04").iterdir())
    run_metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_metadata["execution_mode"] == "replay"


def test_validate_data_includes_lab04(capsys: pytest.CaptureFixture[str]):
    main(["validate-data"])
    captured = capsys.readouterr()
    assert "lab04: OK" in captured.out
