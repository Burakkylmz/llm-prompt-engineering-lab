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


def test_list_command_runs_with_no_labs(capsys: pytest.CaptureFixture[str]):
    main(["list"])
    captured = capsys.readouterr()
    assert "No labs registered yet." in captured.out


def test_main_with_no_args_prints_help(capsys: pytest.CaptureFixture[str]):
    main([])
    captured = capsys.readouterr()
    assert "usage:" in captured.out
