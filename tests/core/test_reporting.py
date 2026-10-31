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


def _paired_run():
    # baseline: c1..c6 -> T F F T F F ; treatment: T T T T F T  => +3 wrong->right, 0 r->w
    baseline = [True, False, False, True, False, False]
    treatment = [True, True, True, True, False, True]
    observations = [_obs("baseline", f"c{i}", v) for i, v in enumerate(baseline, 1)]
    observations += [_obs("treatment", f"c{i}", v) for i, v in enumerate(treatment, 1)]
    return observations


def test_paired_difference_has_bootstrap_ci_and_exploratory_mcnemar():
    summary = build_summary(
        _paired_run(), ["baseline", "treatment"], "baseline", ExecutionMode.FIXTURE
    )
    diff = summary["differences_vs_baseline"]["treatment"]
    assert diff["n_paired_cases"] == 6
    assert diff["accuracy_difference"] == 0.5
    assert diff["ci_low"] <= 0.5 <= diff["ci_high"]
    assert 0.0 <= diff["mcnemar_exact_p_exploratory"] <= 1.0
    assert "baseline" not in summary["differences_vs_baseline"]


def test_paired_difference_is_deterministic_for_a_fixed_seed():
    a = build_summary(_paired_run(), ["baseline", "treatment"], "baseline", ExecutionMode.FIXTURE)
    b = build_summary(_paired_run(), ["baseline", "treatment"], "baseline", ExecutionMode.FIXTURE)
    assert a["differences_vs_baseline"] == b["differences_vs_baseline"]


def test_markdown_labels_mcnemar_exploratory_and_never_claims_significance():
    summary = build_summary(
        _paired_run(), ["baseline", "treatment"], "baseline", ExecutionMode.FIXTURE
    )
    md = render_comparison_markdown(summary, ExecutionMode.FIXTURE)
    assert "exploratory" in md.lower()
    assert "statistically significant" not in md.lower()


def test_macro_f1_has_bootstrap_ci_and_per_class_metrics_with_labels():
    observations = [_obs("baseline", f"c{i}", i % 2 == 0) for i in range(1, 9)]
    summary = build_summary(
        observations,
        ["baseline"],
        "baseline",
        ExecutionMode.FIXTURE,
        labels=["billing", "complaint"],
    )
    cond = summary["per_condition"]["baseline"]
    assert cond["macro_f1_ci_low"] <= cond["macro_f1"] <= cond["macro_f1_ci_high"]
    assert set(cond["per_class"]) == {"billing", "complaint"}
    assert cond["confusion_matrix"]["billing"]["complaint"] == 4
    md = render_comparison_markdown(summary, ExecutionMode.FIXTURE)
    assert "confusion" in md.lower()


def test_per_correct_metrics_stay_null_with_reason_when_unavailable():
    observations = [_obs("baseline", "c1", False), _obs("baseline", "c2", False)]
    cond = build_summary(observations, ["baseline"], "baseline", ExecutionMode.FIXTURE)[
        "per_condition"
    ]["baseline"]
    assert cond["prompt_tokens_per_correct"] == {"value": None, "reason": "no correct responses"}
    # Cost was never priced -> null with a reason, never 0.
    assert cond["cost_per_correct_usd"]["value"] is None
    assert cond["cost_per_correct_usd"]["reason"]
    assert cond["mean_reasoning_tokens"] is None


def test_prompt_tokens_per_correct_divides_total_by_correct_count():
    observations = [_obs("baseline", "c1", True), _obs("baseline", "c2", False)]
    cond = build_summary(observations, ["baseline"], "baseline", ExecutionMode.FIXTURE)[
        "per_condition"
    ]["baseline"]
    assert cond["prompt_tokens_per_correct"]["value"] == 200.0


def test_repetition_consistency_is_none_for_single_repetition():
    cond = build_summary(
        [_obs("baseline", "c1", True)], ["baseline"], "baseline", ExecutionMode.FIXTURE
    )["per_condition"]["baseline"]
    assert cond["repetition_consistency"] is None


def test_repetition_consistency_measures_agreement_across_repetitions():
    observations = [
        _obs("baseline", "c1", True, repetition=1),
        _obs("baseline", "c1", True, repetition=2),
        _obs("baseline", "c2", True, repetition=1),
        _obs("baseline", "c2", False, repetition=2),
    ]
    rc = build_summary(observations, ["baseline"], "baseline", ExecutionMode.FIXTURE)[
        "per_condition"
    ]["baseline"]["repetition_consistency"]
    assert rc["n_repetitions"] == 2
    assert rc["mean_case_consistency"] == 0.75  # c1: 1.0, c2: 0.5
    assert rc["n_fully_consistent_cases"] == 1
    assert rc["accuracy_by_repetition"] == [1.0, 0.5]
    assert rc["accuracy_variance_across_repetitions"] == 0.0625


def test_token_note_differs_between_evidential_and_simulated_modes():
    observations = [_obs("baseline", "c1", True)]
    fixture_md = render_comparison_markdown(
        build_summary(observations, ["baseline"], "baseline", ExecutionMode.FIXTURE),
        ExecutionMode.FIXTURE,
    )
    live_md = render_comparison_markdown(
        build_summary(observations, ["baseline"], "baseline", ExecutionMode.LIVE),
        ExecutionMode.LIVE,
    )
    assert "fake client" in fixture_md
    assert "provider-reported" in live_md


def test_check_rate_denominator_is_only_observations_where_check_was_evaluated():
    """Regression: a check present on only some cases (e.g. Lab 03 `edge_case_correct`)
    must not count the other cases as failures."""
    observations = [_obs("baseline", f"c{i}", True) for i in range(1, 5)]
    # Only c1 and c2 carry the conditional check; one passes, one fails.
    observations[0].evaluation_results["checks"]["edge_case_correct"] = True
    observations[1].evaluation_results["checks"]["edge_case_correct"] = False
    cond = build_summary(observations, ["baseline"], "baseline", ExecutionMode.FIXTURE)[
        "per_condition"
    ]["baseline"]
    edge = cond["constraint_adherence"]["edge_case_correct"]
    assert edge["n_evaluated"] == 2
    assert edge["rate"] == 0.5
    assert cond["constraint_adherence"]["format_ok"]["n_evaluated"] == 4
