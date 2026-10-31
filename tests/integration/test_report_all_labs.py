"""`lab-runner report <run_dir>` must regenerate summary, comparison and *every* chart the
lab's own run produced (spec Section 12), for every lab. Lab 05/06 previously crashed here
(no module-level CONDITION_ORDER) and every lab lost its lab-specific charts."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from lab_core.cli import main

LAB_IDS = [f"lab0{i}" for i in range(1, 9)]


@pytest.mark.parametrize("lab_id", LAB_IDS)
def test_report_regenerates_everything_a_run_produced(lab_id: str, tmp_path: Path):
    results_dir = tmp_path / "results"
    override = tmp_path / "override.toml"
    override.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n', encoding="utf-8"
    )
    main([lab_id, "--config", str(override), "--max-cases", "3"])
    run_dir = next((results_dir / lab_id).iterdir())
    original_charts = sorted(p.name for p in (run_dir / "charts").iterdir())

    shutil.rmtree(run_dir / "charts")
    (run_dir / "summary.json").unlink()
    (run_dir / "comparison.md").unlink()

    main(["report", str(run_dir)])

    assert (run_dir / "summary.json").exists()
    assert (run_dir / "comparison.md").exists()
    assert sorted(p.name for p in (run_dir / "charts").iterdir()) == original_charts
