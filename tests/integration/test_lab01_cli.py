"""End-to-end: CLI -> runner -> fake client -> evaluation -> persistence -> report
(spec Section 14's "Integration" test requirement), plus replay of the committed synthetic
recording fixture under tests/fixtures/recordings/ (spec Section 5's M2 exit criterion)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab_core.cli import main

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_RECORDING = (
    REPO_ROOT / "tests" / "fixtures" / "recordings" / "lab01" / "synthetic-test-recording-001"
)


def _write_results_dir_override(tmp_path: Path) -> Path:
    override = tmp_path / "override.toml"
    results_dir = tmp_path / "results"
    override.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n', encoding="utf-8"
    )
    return override, results_dir


def test_fixture_run_produces_full_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab01", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])

    captured = capsys.readouterr()
    assert "SIMULATED" in captured.out

    run_dirs = list((results_dir / "lab01").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert "_fixture_" in run_dir.name

    assert (run_dir / "run.json").exists()
    assert (run_dir / "observations.jsonl").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "comparison.md").exists()
    assert (run_dir / "charts" / "accuracy_by_condition.png").exists()

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["execution_mode"] == "fixture"
    assert summary["is_evidence_of_model_behavior"] is False
    assert len(summary["per_condition"]) == 6


def test_fixture_run_observation_count_matches_cross_product(tmp_path: Path):
    override, results_dir = _write_results_dir_override(tmp_path)
    main(
        [
            "lab01",
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
    run_dir = next((results_dir / "lab01").iterdir())
    lines = (run_dir / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 6 * 10 * 1  # 6 conditions x 10 cases x 1 repetition


def test_replay_of_synthetic_recording_produces_replay_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    assert SYNTHETIC_RECORDING.exists(), "committed synthetic recording fixture is missing"
    override, results_dir = _write_results_dir_override(tmp_path)

    main(["lab01", "--config", str(override), "--replay", str(SYNTHETIC_RECORDING)])

    captured = capsys.readouterr()
    assert "Replay run written to" in captured.out

    run_dirs = list((results_dir / "lab01").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert "_replay_" in run_dir.name

    run_metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert run_metadata["execution_mode"] == "replay"
    assert run_metadata["source_run_id"] == "synthetic-test-recording-001"

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["execution_mode"] == "replay"

    # Source recording must be untouched by the replay.
    original_run_json = json.loads((SYNTHETIC_RECORDING / "run.json").read_text(encoding="utf-8"))
    assert original_run_json["execution_mode"] == "synthetic_recording_for_tests"


def test_live_without_config_opt_in_is_blocked(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Default config has execution.live_api_enabled=false; --live alone must not reach the
    network (spec Section 13's double-gate requirement)."""
    override, results_dir = _write_results_dir_override(tmp_path)
    main(
        [
            "lab01",
            "--config",
            str(override),
            "--live",
            "--profile",
            "classroom",
            "--max-cases",
            "5",
        ]
    )
    captured = capsys.readouterr()
    assert "[live execution blocked]" in captured.out
    assert "live_api_enabled" in captured.out
    assert not (results_dir / "lab01").exists() or list((results_dir / "lab01").iterdir()) == []


def test_live_requires_confirmation_above_threshold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    override_path = tmp_path / "override.toml"
    results_dir = tmp_path / "results"
    override_path.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n'
        "[execution]\nlive_api_enabled = true\n"
        "[preflight]\nmax_requests_per_run = 10000\nmax_estimated_tokens_per_run = 10000000\n"
        "max_input_tokens_per_request = 100000\nconfirm_above_requests = 1\n",
        encoding="utf-8",
    )
    main(
        [
            "lab01",
            "--config",
            str(override_path),
            "--live",
            "--profile",
            "classroom",
            "--max-cases",
            "5",
        ]
    )
    captured = capsys.readouterr()
    assert "CONFIRMATION REQUIRED" in captured.out
    assert "[live execution blocked] re-run with --yes" in captured.out


def test_replay_detects_prompt_drift_via_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """If the lab's prompt template changes, replay must report the mismatch rather than
    silently reusing stale recorded responses against a different prompt."""
    import labs.lab01_prompt_anatomy.cli as lab01_cli

    monkeypatch.setattr(lab01_cli, "PROMPT_TEMPLATE_VERSION", "lab01-v2-drifted")

    override, results_dir = _write_results_dir_override(tmp_path)
    main(["lab01", "--config", str(override), "--replay", str(SYNTHETIC_RECORDING)])

    captured = capsys.readouterr()
    assert "prompt drift" in captured.out

    run_dir = next((results_dir / "lab01").iterdir())
    lines = (run_dir / "observations.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert lines == []  # all items excluded due to mismatch, none forced through
