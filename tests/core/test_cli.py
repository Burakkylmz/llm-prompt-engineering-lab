from __future__ import annotations

import pytest

from lab_core.cli import build_parser, main


def test_build_parser_help_does_not_crash(capsys: pytest.CaptureFixture[str]):
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "lab-runner" in captured.out


def test_list_command_shows_registered_labs(capsys: pytest.CaptureFixture[str]):
    main(["list"])
    captured = capsys.readouterr()
    assert "lab01" in captured.out


def test_main_with_no_args_prints_help(capsys: pytest.CaptureFixture[str]):
    main([])
    captured = capsys.readouterr()
    assert "usage:" in captured.out


def test_validate_data_reports_ok_for_registered_labs(capsys: pytest.CaptureFixture[str]):
    main(["validate-data"])
    captured = capsys.readouterr()
    assert "lab01: OK" in captured.out


def test_report_regenerates_artifacts_from_existing_run(
    tmp_path, capsys: pytest.CaptureFixture[str]
):
    override = tmp_path / "override.toml"
    results_dir = tmp_path / "results"
    override.write_text(
        f'[experiment]\nresults_dir = "{results_dir.as_posix()}"\n', encoding="utf-8"
    )
    main(["lab01", "--config", str(override), "--profile", "classroom", "--max-cases", "10"])
    run_dir = next((results_dir / "lab01").iterdir())

    (run_dir / "summary.json").unlink()
    main(["report", str(run_dir)])

    captured = capsys.readouterr()
    assert "Report regenerated" in captured.out
    assert (run_dir / "summary.json").exists()
