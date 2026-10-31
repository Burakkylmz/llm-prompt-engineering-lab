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


def test_fixture_run_shows_the_gap(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab08", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])

    captured = capsys.readouterr()
    assert "SIMULATED" in captured.out

    run_dir = next((results_dir / "lab08").iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert len(summary["per_condition"]) == 5
    assert summary["per_condition"]["plain_nl"]["accuracy"] == 0.0
    assert summary["per_condition"]["json_schema_strict"]["accuracy"] == 1.0
    assert (run_dir / "charts" / "three_layer_results.png").exists()


def test_observation_count_matches_cross_product(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(
        [
            "lab08",
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
    run_dir = next((results_dir / "lab08").iterdir())
    lines = (run_dir / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5 * 10 * 1


def test_validate_data_includes_lab08(capsys: pytest.CaptureFixture[str]):
    main(["validate-data"])
    captured = capsys.readouterr()
    assert "lab08: OK" in captured.out


SYNTHETIC_RECORDING = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "recordings"
    / "lab08"
    / "synthetic-test-recording-001"
)


def test_replay_of_synthetic_recording_reevaluates_all_three_layers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """The recording's hand-written responses each fail at a different layer, so a correct
    replay must reproduce exactly that pattern: valid JSON != schema-compliant JSON !=
    semantically correct data."""
    assert SYNTHETIC_RECORDING.exists()
    override, results_dir = _write_results_dir_override(tmp_path)
    main(
        [
            "lab08",
            "--config",
            str(override),
            "--replay",
            str(SYNTHETIC_RECORDING),
            "--max-cases",
            "1000",
        ]
    )
    assert "prompt drift" not in capsys.readouterr().out

    run_dir = next((results_dir / "lab08").iterdir())
    run_metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_metadata["execution_mode"] == "replay"

    observations = [
        json.loads(line)
        for line in (run_dir / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    layers = {
        (o["condition_id"], o["case_id"]): (
            o["evaluation_results"]["checks"]["json_parse_success"],
            o["evaluation_results"]["checks"]["schema_adherent"],
            o["evaluation_results"]["checks"]["semantic_correct"],
        )
        for o in observations
    }
    assert layers == {
        ("plain_nl", "lab08-rec-001"): (False, False, False),
        ("prompt_only_json", "lab08-rec-001"): (True, True, True),
        ("json_schema_strict", "lab08-rec-001"): (True, True, True),
        ("json_object_mode", "lab08-rec-002"): (True, False, False),
        ("json_schema_best_effort", "lab08-rec-002"): (True, True, False),
        ("json_schema_strict", "lab08-rec-002"): (True, True, True),
    }
    for o in observations:
        assert o["source_run_id"] == "synthetic-test-recording-001"
