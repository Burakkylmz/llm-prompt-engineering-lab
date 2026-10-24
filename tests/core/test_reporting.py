from __future__ import annotations

from pathlib import Path

from lab_core.execution_mode import ExecutionMode
from lab_core.metrics import CostEstimate, PerformanceMetrics, UsageMetrics
from lab_core.reporting import build_summary, render_comparison_markdown, write_full_report
from lab_core.results_writer import Observation


def _obs(condition_id, case_id, correct, repetition=1, skip_reason=None, error=None):
    return Observation(
        experiment_id="lab01:run1",
        lab_id="lab01",
        run_id="run1",
        condition_id=condition_id,
        case_id=case_id,
        repetition=repetition,
        execution_mode="fixture",
        timestamp="2026-10-24T00:00:00Z",
        model_id="m",
        generation_parameters={},
        prompt_template_version="v1",
        prompt_hash="h",
        dataset_version="v1",
        raw_response="billing" if correct else "complaint",
        expected_output={"label": "billing"},
        evaluation_results={}
        if (skip_reason or error)
        else {
            "checks": {"format_ok": correct},
            "primary_correct": correct,
            "parsed_label": "billing" if correct else "complaint",
            "notes": {},
        },
        usage=UsageMetrics(prompt_tokens=100, completion_tokens=5),
        performance=PerformanceMetrics(client_elapsed_ms=10.0),
        cost=CostEstimate(None, reason="no pricing"),
        skip_reason=skip_reason,
        error=error,
    )


def test_summary_accuracy_reflects_correct_rate():
    observations = [
        _obs("baseline", "c1", True),
        _obs("baseline", "c2", False),
        _obs("baseline", "c3", True),
        _obs("baseline", "c4", True),
    ]
    summary = build_summary(observations, ["baseline"], "baseline", ExecutionMode.FIXTURE)
    assert summary["per_condition"]["baseline"]["accuracy"] == 0.75
    assert summary["per_condition"]["baseline"]["n_usable"] == 4


def test_summary_excludes_skipped_and_errored_from_accuracy_denominator():
    observations = [
        _obs("baseline", "c1", True),
        _obs("baseline", "c2", False, skip_reason="unsupported:x"),
        _obs("baseline", "c3", False, error="boom"),
    ]
    summary = build_summary(observations, ["baseline"], "baseline", ExecutionMode.FIXTURE)
    cond = summary["per_condition"]["baseline"]
    assert cond["n_usable"] == 1
    assert cond["n_skipped"] == 1
    assert cond["n_errored"] == 1
    assert cond["accuracy"] == 1.0


def test_flips_computed_between_baseline_and_treatment():
    observations = [
        _obs("baseline", "c1", False),
        _obs("baseline", "c2", True),
        _obs("treatment", "c1", True),  # wrong -> right
        _obs("treatment", "c2", False),  # right -> wrong
    ]
    summary = build_summary(
        observations, ["baseline", "treatment"], "baseline", ExecutionMode.FIXTURE
    )
    flips = summary["flips_vs_baseline"]["treatment"]
    assert flips["wrong_to_right"] == ["c1"]
    assert flips["right_to_wrong"] == ["c2"]
    assert flips["net_improvement"] == 0


def test_markdown_contains_mode_banner_and_simulated_caution():
    observations = [_obs("baseline", "c1", True)]
    summary = build_summary(observations, ["baseline"], "baseline", ExecutionMode.FIXTURE)
    markdown = render_comparison_markdown(summary, ExecutionMode.FIXTURE)
    assert "SIMULATED" in markdown
    assert "pipeline only" in markdown


def test_markdown_does_not_claim_simulated_for_live_mode():
    observations = [_obs("baseline", "c1", True)]
    summary = build_summary(observations, ["baseline"], "baseline", ExecutionMode.LIVE)
    markdown = render_comparison_markdown(summary, ExecutionMode.LIVE)
    assert "SIMULATED" not in markdown


def test_write_full_report_creates_all_artifacts(tmp_path: Path):
    observations = [
        _obs("baseline", "c1", True),
        _obs("baseline", "c2", False),
        _obs("treatment", "c1", True),
        _obs("treatment", "c2", True),
    ]
    write_full_report(
        tmp_path, observations, ["baseline", "treatment"], "baseline", ExecutionMode.FIXTURE
    )
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "comparison.md").exists()
    assert (tmp_path / "charts" / "accuracy_by_condition.png").exists()
