"""Builds `summary.json`, `comparison.md`, and charts from a list of `Observation`s
(spec Sections 10 and 12). The single code path used both right after a run and by the
standalone `lab-runner report <run_dir>` command.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.evaluation import classification_metrics
from lab_core.execution_mode import ExecutionMode
from lab_core.results_writer import Observation
from lab_core.statistics import (
    bootstrap_ci,
    cis_overlap_substantially,
    mcnemar_exact,
    mean,
    paired_flips,
    wilson_ci,
)

DEFAULT_BOOTSTRAP_RESAMPLES = 1000
DEFAULT_BOOTSTRAP_SEED = 20261024


def _usable(observations: list[Observation]) -> list[Observation]:
    """Observations that produced a real evaluation — excludes skipped/errored items, which
    are reported separately as counts rather than folded silently into the denominator."""
    return [o for o in observations if o.skip_reason is None and o.error is None]


def _mean_of_reported(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return mean(present) if present else None


def _sum_of_reported(values: list[float | None]) -> float | None:
    """Sum only when *every* value was reported — a partial sum would silently understate
    the total, which is worse than reporting it as unavailable."""
    if not values or any(v is None for v in values):
        return None
    return float(sum(v for v in values if v is not None))


def _per_correct(total: float | None, n_correct: int) -> dict[str, Any]:
    if total is None:
        return {"value": None, "reason": "not reported for every usable observation"}
    if n_correct == 0:
        return {"value": None, "reason": "no correct responses"}
    return {"value": total / n_correct, "reason": None}


def _repetition_consistency(usable: list[Observation]) -> dict[str, Any] | None:
    """Spec Section 10: with repetitions > 1, report per-case consistency (share of
    repetitions agreeing with that case's most common outcome) and the variance of
    accuracy across repetitions. Returns None for single-repetition runs, where neither is
    defined — not 1.0, which would wrongly suggest measured stability."""
    repetitions = sorted({o.repetition for o in usable})
    if len(repetitions) < 2:
        return None

    outcomes_by_case: dict[str, list[str]] = defaultdict(list)
    for o in usable:
        outcome = o.evaluation_results.get("parsed_label")
        if outcome is None:
            outcome = "correct" if o.evaluation_results.get("primary_correct") else "incorrect"
        outcomes_by_case[o.case_id].append(str(outcome))
    per_case = {
        case_id: max(outcomes.count(x) for x in set(outcomes)) / len(outcomes)
        for case_id, outcomes in outcomes_by_case.items()
        if len(outcomes) > 1
    }

    accuracy_by_rep = []
    for rep in repetitions:
        rep_obs = [o for o in usable if o.repetition == rep]
        if rep_obs:
            accuracy_by_rep.append(
                sum(1 for o in rep_obs if o.evaluation_results.get("primary_correct"))
                / len(rep_obs)
            )
    rep_mean = mean(accuracy_by_rep)
    variance = sum((a - rep_mean) ** 2 for a in accuracy_by_rep) / len(accuracy_by_rep)

    return {
        "n_repetitions": len(repetitions),
        "mean_case_consistency": mean(list(per_case.values())) if per_case else None,
        "n_fully_consistent_cases": sum(1 for v in per_case.values() if v == 1.0),
        "n_cases": len(per_case),
        "accuracy_by_repetition": accuracy_by_rep,
        "accuracy_variance_across_repetitions": variance,
    }


def summarize_condition(
    observations: list[Observation],
    labels: list[str] | None = None,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Any]:
    usable = _usable(observations)
    n_total = len(observations)
    n_usable = len(usable)
    n_skipped = sum(1 for o in observations if o.skip_reason is not None)
    n_errored = sum(1 for o in observations if o.error is not None)

    successes = sum(1 for o in usable if o.evaluation_results.get("primary_correct"))
    accuracy_ci = wilson_ci(successes, n_usable) if n_usable else None

    constraint_rates: dict[str, Any] = {}
    all_constraint_names: set[str] = set()
    for o in usable:
        all_constraint_names.update(o.evaluation_results.get("checks", {}).keys())
    for name in sorted(all_constraint_names):
        # Denominator = observations where this check was actually evaluated. Some checks
        # only apply to a subset of cases (e.g. Lab 03's `edge_case_correct`, Lab 02's
        # `false_refusal` on benign controls); dividing by every usable observation would
        # silently count "not applicable" as "failed" and dilute the rate.
        evaluated = [o for o in usable if name in o.evaluation_results.get("checks", {})]
        passed = sum(1 for o in evaluated if o.evaluation_results["checks"][name])
        ci = wilson_ci(passed, len(evaluated)) if evaluated else None
        constraint_rates[name] = {
            "rate": ci.point_estimate if ci else None,
            "ci_low": ci.low if ci else None,
            "ci_high": ci.high if ci else None,
            "n_evaluated": len(evaluated),
        }

    macro_f1 = None
    macro_f1_ci = None
    per_class = None
    confusion_matrix = None
    if labels:
        pairs = [
            (o.evaluation_results.get("parsed_label") or "", o.expected_output.get("label", ""))
            for o in usable
        ]
        if pairs:
            metrics = classification_metrics(pairs, labels)
            macro_f1 = metrics.macro_f1
            per_class = {
                label: {
                    "precision": metrics.per_class_precision[label],
                    "recall": metrics.per_class_recall[label],
                    "f1": metrics.per_class_f1[label],
                }
                for label in labels
            }
            confusion_matrix = metrics.confusion_matrix
            ci = bootstrap_ci(
                pairs,
                lambda sample: classification_metrics(list(sample), labels).macro_f1,
                resamples=bootstrap_resamples,
                seed=bootstrap_seed,
            )
            macro_f1_ci = {"low": ci.low, "high": ci.high}

    prompt_tokens = _mean_of_reported([o.usage.prompt_tokens for o in usable])
    completion_tokens = _mean_of_reported([o.usage.completion_tokens for o in usable])
    latency_ms = _mean_of_reported([o.performance.client_elapsed_ms for o in usable])
    cost_usd = _mean_of_reported([o.cost.estimated_cost_usd for o in usable])
    reasoning_tokens = _mean_of_reported([o.usage.reasoning_tokens for o in usable])

    return {
        "n_total": n_total,
        "n_usable": n_usable,
        "n_skipped": n_skipped,
        "n_errored": n_errored,
        "accuracy": accuracy_ci.point_estimate if accuracy_ci else None,
        "accuracy_ci_low": accuracy_ci.low if accuracy_ci else None,
        "accuracy_ci_high": accuracy_ci.high if accuracy_ci else None,
        "macro_f1": macro_f1,
        "macro_f1_ci_low": macro_f1_ci["low"] if macro_f1_ci else None,
        "macro_f1_ci_high": macro_f1_ci["high"] if macro_f1_ci else None,
        "per_class": per_class,
        "confusion_matrix": confusion_matrix,
        "constraint_adherence": constraint_rates,
        "mean_prompt_tokens": prompt_tokens,
        "mean_completion_tokens": completion_tokens,
        "mean_latency_ms": latency_ms,
        "mean_cost_usd": cost_usd,
        "mean_reasoning_tokens": reasoning_tokens,
        "prompt_tokens_per_correct": _per_correct(
            _sum_of_reported([o.usage.prompt_tokens for o in usable]), successes
        ),
        "cost_per_correct_usd": _per_correct(
            _sum_of_reported([o.cost.estimated_cost_usd for o in usable]), successes
        ),
        "repetition_consistency": _repetition_consistency(usable),
    }


def _primary_correct_by_case(
    observations: list[Observation], repetition: int = 1
) -> dict[str, bool]:
    return {
        o.case_id: bool(o.evaluation_results.get("primary_correct"))
        for o in _usable(observations)
        if o.repetition == repetition
    }


def build_summary(
    observations: list[Observation],
    condition_order: list[str],
    baseline_condition_id: str,
    execution_mode: ExecutionMode,
    labels: list[str] | None = None,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Any]:
    by_condition: dict[str, list[Observation]] = defaultdict(list)
    for o in observations:
        by_condition[o.condition_id].append(o)

    per_condition = {
        cid: summarize_condition(
            by_condition.get(cid, []),
            labels=labels,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        for cid in condition_order
    }

    baseline_by_case = _primary_correct_by_case(by_condition.get(baseline_condition_id, []))
    flips: dict[str, Any] = {}
    differences: dict[str, Any] = {}
    for cid in condition_order:
        if cid == baseline_condition_id:
            continue
        treatment_by_case = _primary_correct_by_case(by_condition.get(cid, []))
        common_cases = set(baseline_by_case) & set(treatment_by_case)
        if not common_cases:
            continue
        pf = paired_flips(
            {k: baseline_by_case[k] for k in common_cases},
            {k: treatment_by_case[k] for k in common_cases},
        )
        flips[cid] = {
            "wrong_to_right": pf.wrong_to_right,
            "right_to_wrong": pf.right_to_wrong,
            "net_improvement": pf.net_improvement,
        }
        # Paired difference in accuracy (treatment - baseline) over the shared case set,
        # with a seeded percentile bootstrap CI over per-case differences (spec Section 10).
        # McNemar is included strictly as an EXPLORATORY figure: no significance claim is
        # made from it anywhere in the generated reports.
        ordered_cases = sorted(common_cases)
        per_case_diff = [
            float(treatment_by_case[k]) - float(baseline_by_case[k]) for k in ordered_cases
        ]
        diff_ci = bootstrap_ci(
            per_case_diff, mean, resamples=bootstrap_resamples, seed=bootstrap_seed
        )
        differences[cid] = {
            "n_paired_cases": len(ordered_cases),
            "accuracy_difference": diff_ci.point_estimate,
            "ci_low": diff_ci.low,
            "ci_high": diff_ci.high,
            "ci_method": f"paired percentile bootstrap, {bootstrap_resamples} resamples, "
            f"seed {bootstrap_seed}",
            "mcnemar_exact_p_exploratory": mcnemar_exact(
                len(pf.wrong_to_right), len(pf.right_to_wrong)
            ),
        }

    return {
        "execution_mode": execution_mode.value,
        "is_evidence_of_model_behavior": execution_mode.is_evidence_of_model_behavior,
        "condition_order": condition_order,
        "baseline_condition_id": baseline_condition_id,
        "per_condition": per_condition,
        "flips_vs_baseline": flips,
        "differences_vs_baseline": differences,
        "flips_and_differences_use_repetition": 1,
    }


def render_comparison_markdown(summary: dict[str, Any], execution_mode: ExecutionMode) -> str:
    lines = ["# Comparison Report\n", f"**Mode: {execution_mode.banner}**\n"]
    if not execution_mode.is_evidence_of_model_behavior:
        lines.append(
            "> This report was produced in a non-evidential execution mode. It validates "
            "the pipeline only and must not be read as a claim about real model behavior.\n"
        )

    lines.append("## Conditions\n")
    lines.append(
        "| Condition | n (usable) | Skipped | Errored | Accuracy | 95% CI | "
        "Macro-F1 [95% bootstrap CI] |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    baseline_id = summary["baseline_condition_id"]
    baseline_summary = summary["per_condition"].get(baseline_id, {})
    baseline_ci = (
        (baseline_summary.get("accuracy_ci_low"), baseline_summary.get("accuracy_ci_high"))
        if baseline_summary.get("accuracy") is not None
        else None
    )
    caution_conditions: list[str] = []
    for cid in summary["condition_order"]:
        cond = summary["per_condition"].get(cid, {})
        accuracy = cond.get("accuracy")
        ci_text = (
            f"[{cond['accuracy_ci_low']:.2f}, {cond['accuracy_ci_high']:.2f}]"
            if accuracy is not None
            else "-"
        )
        lines.append(
            f"| {cid} | {cond.get('n_usable', 0)} | {cond.get('n_skipped', 0)} | "
            f"{cond.get('n_errored', 0)} | "
            f"{f'{accuracy:.2%}' if accuracy is not None else '-'} | {ci_text} | "
            f"{_format_macro_f1(cond)} |"
        )
        if cid != baseline_id and accuracy is not None and baseline_ci is not None:
            from lab_core.statistics import ConfidenceInterval

            this_ci = ConfidenceInterval(
                point_estimate=accuracy,
                low=cond["accuracy_ci_low"],
                high=cond["accuracy_ci_high"],
                n=cond["n_usable"],
            )
            base_ci_obj = ConfidenceInterval(
                point_estimate=baseline_summary["accuracy"],
                low=baseline_ci[0],
                high=baseline_ci[1],
                n=baseline_summary["n_usable"],
            )
            if cis_overlap_substantially(this_ci, base_ci_obj):
                caution_conditions.append(cid)

    if caution_conditions:
        lines.append(
            "\n> **Caution:** the confidence interval for "
            + ", ".join(caution_conditions)
            + " overlaps substantially with the baseline's. "
            "Differences within this run may be noise."
        )

    lines.append("\n## Per-case flips vs. baseline\n")
    for cid, flip in summary["flips_vs_baseline"].items():
        lines.append(
            f"- **{cid}**: {len(flip['wrong_to_right'])} wrong->right, "
            f"{len(flip['right_to_wrong'])} right->wrong (net {flip['net_improvement']:+d})"
        )

    lines.extend(_render_differences_section(summary))
    lines.extend(_render_adherence_section(summary))
    lines.extend(_render_efficiency_section(summary))
    lines.extend(_render_classification_section(summary))
    lines.extend(_render_consistency_section(summary))
    return "\n".join(lines) + "\n"


def _fmt(value: float | None, spec: str = ".2%") -> str:
    return format(value, spec) if value is not None else "-"


def _format_macro_f1(cond: dict[str, Any]) -> str:
    macro_f1 = cond.get("macro_f1")
    if macro_f1 is None:
        return "-"
    low, high = cond.get("macro_f1_ci_low"), cond.get("macro_f1_ci_high")
    if low is None or high is None:
        return f"{macro_f1:.3f}"
    return f"{macro_f1:.3f} [{low:.3f}, {high:.3f}]"


def _render_differences_section(summary: dict[str, Any]) -> list[str]:
    differences = summary.get("differences_vs_baseline") or {}
    if not differences:
        return []
    lines = [
        "\n## Accuracy difference vs. baseline (paired)\n",
        "Computed over the cases both conditions share (repetition 1). The CI is a seeded "
        "percentile bootstrap over per-case differences. The McNemar p-value is "
        "**exploratory only** and is not a significance claim; classroom-sized runs are far "
        "too small to support one (see `docs/statistics.md`).\n",
        "| Condition | Paired n | Difference | 95% bootstrap CI | McNemar p (exploratory) |",
        "|---|---|---|---|---|",
    ]
    for cid in summary["condition_order"]:
        d = differences.get(cid)
        if d is None:
            continue
        lines.append(
            f"| {cid} | {d['n_paired_cases']} | {d['accuracy_difference']:+.2%} | "
            f"[{d['ci_low']:+.2%}, {d['ci_high']:+.2%}] | "
            f"{d['mcnemar_exact_p_exploratory']:.3f} |"
        )
    crossing = [cid for cid, d in differences.items() if d["ci_low"] <= 0 <= d["ci_high"]]
    if crossing:
        lines.append(
            "\n> **Caution:** the difference CI includes 0 for "
            + ", ".join(c for c in summary["condition_order"] if c in crossing)
            + ". The direction of these differences is not established by this run."
        )
    return lines


def _render_adherence_section(summary: dict[str, Any]) -> list[str]:
    """One row per evaluator check (instruction-adherence constraint, injection check,
    schema layer, ...), one column per condition: rate with its 95% Wilson CI. Checks a
    condition never produced are shown as '-' (absent), never as 0%."""
    per_condition = summary["per_condition"]
    condition_ids = summary["condition_order"]
    check_names = sorted(
        {name for cid in condition_ids for name in per_condition[cid]["constraint_adherence"]}
    )
    if not check_names:
        return []
    lines = [
        "\n## Per-check rates (95% Wilson CI)\n",
        "Each evaluator check is reported separately; see the lab README for what each check "
        "means and which conditions it is expected to apply to.\n",
        "| Check | " + " | ".join(condition_ids) + " |",
        "|---|" + "---|" * len(condition_ids),
    ]
    for name in check_names:
        cells = []
        for cid in condition_ids:
            rate = per_condition[cid]["constraint_adherence"].get(name)
            if rate is None or rate["rate"] is None:
                cells.append("-")
            else:
                cells.append(f"{rate['rate']:.0%} [{rate['ci_low']:.2f}, {rate['ci_high']:.2f}]")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return lines


def _render_efficiency_section(summary: dict[str, Any]) -> list[str]:
    lines = [
        "\n## Tokens, latency and cost\n",
        _token_source_note(summary),
        "| Condition | Mean prompt tokens | Mean completion tokens | Mean reasoning tokens | "
        "Prompt tokens per correct | Mean latency (ms) | Cost per correct (USD) |",
        "|---|---|---|---|---|---|---|",
    ]
    for cid in summary["condition_order"]:
        c = summary["per_condition"][cid]
        tpc = c["prompt_tokens_per_correct"]
        cpc = c["cost_per_correct_usd"]
        lines.append(
            f"| {cid} | {_fmt(c['mean_prompt_tokens'], '.1f')} | "
            f"{_fmt(c['mean_completion_tokens'], '.1f')} | "
            f"{_fmt(c['mean_reasoning_tokens'], '.1f')} | "
            f"{_fmt(tpc['value'], '.1f')} | {_fmt(c['mean_latency_ms'], '.1f')} | "
            f"{_fmt(cpc['value'], '.6f')} |"
        )
    return lines


def _token_source_note(summary: dict[str, Any]) -> str:
    if summary.get("is_evidence_of_model_behavior"):
        return (
            "Token figures are **provider-reported** usage ('-' when the provider did not "
            "report a field); they are never local estimates. Cost appears only with "
            "verified, dated pricing.\n"
        )
    return (
        "**Non-evidential mode:** these token figures come from the fake client's local "
        "estimator, not from a provider. They show the relative prompt size of each "
        "condition, not measured usage.\n"
    )


def _render_classification_section(summary: dict[str, Any]) -> list[str]:
    per_condition = summary["per_condition"]
    condition_ids = [c for c in summary["condition_order"] if per_condition[c].get("per_class")]
    if not condition_ids:
        return []
    lines = [
        "\n## Per-class precision / recall and confusion matrices\n",
        "Headline accuracy can hide which classes are confused; read these alongside it.\n",
    ]
    for cid in condition_ids:
        cond = per_condition[cid]
        labels = list(cond["per_class"].keys())
        lines.append(f"\n### {cid}\n")
        lines.append("| Class | Precision | Recall | F1 |")
        lines.append("|---|---|---|---|")
        for label in labels:
            m = cond["per_class"][label]
            lines.append(f"| {label} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} |")
        confusion = cond["confusion_matrix"]
        predicted_columns = list(labels)
        for row in confusion.values():
            for predicted in row:
                if predicted not in predicted_columns:
                    predicted_columns.append(predicted)
        header = [p if p else "(unparsed)" for p in predicted_columns]
        lines.append("\nRows = gold, columns = predicted.\n")
        lines.append("| gold \\ predicted | " + " | ".join(header) + " |")
        lines.append("|---|" + "---|" * len(header))
        for gold, row in confusion.items():
            lines.append(
                f"| {gold} | " + " | ".join(str(row.get(p, 0)) for p in predicted_columns) + " |"
            )
    return lines


def _render_consistency_section(summary: dict[str, Any]) -> list[str]:
    rows = [
        (cid, summary["per_condition"][cid]["repetition_consistency"])
        for cid in summary["condition_order"]
        if summary["per_condition"][cid].get("repetition_consistency")
    ]
    if not rows:
        return []
    lines = [
        "\n## Consistency across repetitions\n",
        "An API seed does not guarantee identical outputs; this shows how often repeated "
        "calls on the same case agreed.\n",
        "| Condition | Repetitions | Mean per-case consistency | Fully consistent cases | "
        "Accuracy variance across repetitions |",
        "|---|---|---|---|---|",
    ]
    for cid, rc in rows:
        lines.append(
            f"| {cid} | {rc['n_repetitions']} | {_fmt(rc['mean_case_consistency'])} | "
            f"{rc['n_fully_consistent_cases']}/{rc['n_cases']} | "
            f"{rc['accuracy_variance_across_repetitions']:.4f} |"
        )
    return lines


def render_accuracy_chart(
    summary: dict[str, Any], execution_mode: ExecutionMode, output_path: Path
) -> Path:
    condition_ids = summary["condition_order"]
    accuracies = [summary["per_condition"][c].get("accuracy") for c in condition_ids]
    los = [summary["per_condition"][c].get("accuracy_ci_low") for c in condition_ids]
    his = [summary["per_condition"][c].get("accuracy_ci_high") for c in condition_ids]

    x = range(len(condition_ids))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    values = [a if a is not None else 0 for a in accuracies]
    err_low = [
        (v - lo) if (v is not None and lo is not None) else 0
        for v, lo in zip(accuracies, los, strict=True)
    ]
    err_high = [
        (hi - v) if (v is not None and hi is not None) else 0
        for v, hi in zip(accuracies, his, strict=True)
    ]
    ax.bar(x, values, yerr=[err_low, err_high], capsize=4, color="#4C72B0")
    ax.set_xticks(list(x))
    ax.set_xticklabels(condition_ids, rotation=30, ha="right")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1)
    title = "Accuracy by condition (95% Wilson CI)"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path


def write_full_report(
    run_dir: Path,
    observations: list[Observation],
    condition_order: list[str],
    baseline_condition_id: str,
    execution_mode: ExecutionMode,
    labels: list[str] | None = None,
) -> None:
    """The single entry point used both right after a run and by `lab-runner report`."""
    summary = build_summary(
        observations, condition_order, baseline_condition_id, execution_mode, labels
    )
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    (run_dir / "comparison.md").write_text(
        render_comparison_markdown(summary, execution_mode), encoding="utf-8"
    )
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    render_accuracy_chart(summary, execution_mode, charts_dir / "accuracy_by_condition.png")


def build_reference_comparison(
    observations: list[Observation],
    reference_condition_id: str,
    condition_ids: list[str],
    execution_mode: ExecutionMode,
    labels: list[str] | None = None,
    extra_checks: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Compare `condition_ids` against a *reference* condition other than the run's baseline
    (e.g. Lab 01's leave-one-out ablation vs. the full prompt, Lab 03's example-order series
    vs. the original order). Uses exactly the same paired-difference, bootstrap and flip code
    as the main report, so the two can never disagree about method."""
    subset = [o for o in observations if o.condition_id in {reference_condition_id, *condition_ids}]
    summary = build_summary(
        subset,
        [reference_condition_id, *condition_ids],
        reference_condition_id,
        execution_mode,
        labels=labels,
    )

    def _row(cid: str) -> dict[str, Any]:
        cond = summary["per_condition"][cid]
        diff = summary["differences_vs_baseline"].get(cid)
        flips = summary["flips_vs_baseline"].get(cid)
        return {
            "condition_id": cid,
            "n_usable": cond["n_usable"],
            "accuracy": cond["accuracy"],
            "macro_f1": cond["macro_f1"],
            "mean_prompt_tokens": cond["mean_prompt_tokens"],
            "checks": {
                name: cond["constraint_adherence"].get(name, {}).get("rate")
                for name in extra_checks
            },
            "accuracy_difference": diff["accuracy_difference"] if diff else None,
            "difference_ci_low": diff["ci_low"] if diff else None,
            "difference_ci_high": diff["ci_high"] if diff else None,
            "wrong_to_right": len(flips["wrong_to_right"]) if flips else None,
            "right_to_wrong": len(flips["right_to_wrong"]) if flips else None,
        }

    return {
        "reference": _row(reference_condition_id),
        "rows": [_row(cid) for cid in condition_ids],
    }


def render_reference_comparison_markdown(
    title: str,
    intro: str,
    comparison: dict[str, Any],
    row_labels: dict[str, str] | None = None,
    row_label_header: str = "Condition",
) -> str:
    row_labels = row_labels or {}
    extra = list(comparison["reference"]["checks"].keys())
    ref = comparison["reference"]
    label_col = f"| {row_label_header} " if row_labels else ""
    header = (
        f"{label_col}| Condition | Accuracy | "
        + "".join(f"{name} | " for name in extra)
        + "Difference vs. reference [95% bootstrap CI] | wrong->right / right->wrong | "
        "Mean prompt tokens |"
    )
    lines = [
        f"\n## {title}\n",
        intro + "\n",
        f"Reference `{ref['condition_id']}`: accuracy {_fmt(ref['accuracy'], '.0%')}"
        + "".join(f", {name} {_fmt(ref['checks'][name], '.0%')}" for name in extra)
        + ".\n",
        header,
        ("|---" if row_labels else "") + "|---|---|" + "---|" * len(extra) + "---|---|---|",
    ]
    for r in comparison["rows"]:
        diff = (
            f"{r['accuracy_difference']:+.0%} "
            f"[{r['difference_ci_low']:+.0%}, {r['difference_ci_high']:+.0%}]"
            if r["accuracy_difference"] is not None
            else "-"
        )
        flips = (
            f"{r['wrong_to_right']} / {r['right_to_wrong']}"
            if r["wrong_to_right"] is not None
            else "-"
        )
        lines.append(
            (f"| {row_labels.get(r['condition_id'], r['condition_id'])} " if row_labels else "")
            + f"| {r['condition_id']} | "
            f"{_fmt(r['accuracy'], '.0%')} | "
            + "".join(f"{_fmt(r['checks'][name], '.0%')} | " for name in extra)
            + f"{diff} | {flips} | {_fmt(r['mean_prompt_tokens'], '.0f')} |"
        )
    if any(
        r["difference_ci_low"] is not None
        and r["difference_ci_low"] <= 0 <= r["difference_ci_high"]
        for r in comparison["rows"]
    ):
        lines.append(
            "\n> **Caution:** at least one difference CI includes 0; this run does not "
            "establish the direction of those differences."
        )
    return "\n".join(lines) + "\n"
