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
from lab_core.statistics import cis_overlap_substantially, mean, paired_flips, wilson_ci


def _usable(observations: list[Observation]) -> list[Observation]:
    """Observations that produced a real evaluation — excludes skipped/errored items, which
    are reported separately as counts rather than folded silently into the denominator."""
    return [o for o in observations if o.skip_reason is None and o.error is None]


def _mean_of_reported(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return mean(present) if present else None


def summarize_condition(
    observations: list[Observation], labels: list[str] | None = None
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
        passed = sum(1 for o in usable if o.evaluation_results.get("checks", {}).get(name))
        ci = wilson_ci(passed, n_usable) if n_usable else None
        constraint_rates[name] = {
            "rate": ci.point_estimate if ci else None,
            "ci_low": ci.low if ci else None,
            "ci_high": ci.high if ci else None,
        }

    macro_f1 = None
    if labels:
        pairs = [
            (o.evaluation_results.get("parsed_label") or "", o.expected_output.get("label", ""))
            for o in usable
        ]
        if pairs:
            macro_f1 = classification_metrics(pairs, labels).macro_f1

    prompt_tokens = _mean_of_reported([o.usage.prompt_tokens for o in usable])
    completion_tokens = _mean_of_reported([o.usage.completion_tokens for o in usable])
    latency_ms = _mean_of_reported([o.performance.client_elapsed_ms for o in usable])
    cost_usd = _mean_of_reported([o.cost.estimated_cost_usd for o in usable])

    return {
        "n_total": n_total,
        "n_usable": n_usable,
        "n_skipped": n_skipped,
        "n_errored": n_errored,
        "accuracy": accuracy_ci.point_estimate if accuracy_ci else None,
        "accuracy_ci_low": accuracy_ci.low if accuracy_ci else None,
        "accuracy_ci_high": accuracy_ci.high if accuracy_ci else None,
        "macro_f1": macro_f1,
        "constraint_adherence": constraint_rates,
        "mean_prompt_tokens": prompt_tokens,
        "mean_completion_tokens": completion_tokens,
        "mean_latency_ms": latency_ms,
        "mean_cost_usd": cost_usd,
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
) -> dict[str, Any]:
    by_condition: dict[str, list[Observation]] = defaultdict(list)
    for o in observations:
        by_condition[o.condition_id].append(o)

    per_condition = {
        cid: summarize_condition(by_condition.get(cid, []), labels=labels)
        for cid in condition_order
    }

    baseline_by_case = _primary_correct_by_case(by_condition.get(baseline_condition_id, []))
    flips: dict[str, Any] = {}
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

    return {
        "execution_mode": execution_mode.value,
        "is_evidence_of_model_behavior": execution_mode.is_evidence_of_model_behavior,
        "condition_order": condition_order,
        "baseline_condition_id": baseline_condition_id,
        "per_condition": per_condition,
        "flips_vs_baseline": flips,
    }


def render_comparison_markdown(summary: dict[str, Any], execution_mode: ExecutionMode) -> str:
    lines = ["# Comparison Report\n", f"**Mode: {execution_mode.banner}**\n"]
    if not execution_mode.is_evidence_of_model_behavior:
        lines.append(
            "> This report was produced in a non-evidential execution mode. It validates "
            "the pipeline only and must not be read as a claim about real model behavior.\n"
        )

    lines.append("## Conditions\n")
    lines.append("| Condition | n (usable) | Skipped | Errored | Accuracy | 95% CI | Macro-F1 |")
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
        macro_f1 = cond.get("macro_f1")
        lines.append(
            f"| {cid} | {cond.get('n_usable', 0)} | {cond.get('n_skipped', 0)} | "
            f"{cond.get('n_errored', 0)} | "
            f"{f'{accuracy:.2%}' if accuracy is not None else '-'} | {ci_text} | "
            f"{f'{macro_f1:.3f}' if macro_f1 is not None else '-'} |"
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

    return "\n".join(lines) + "\n"


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
