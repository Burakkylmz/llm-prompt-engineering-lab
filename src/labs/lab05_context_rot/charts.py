"""Lab 05's priority chart (spec Section 12): accuracy vs. context length, with 95% Wilson
CI error bars, plus the not-found and hallucination rates for context."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.execution_mode import ExecutionMode


def render_length_curve_chart(
    summary: dict[str, Any], lengths: list[int], execution_mode: ExecutionMode, output_path: Path
) -> Path:
    condition_ids = [f"length_{length}" for length in lengths]
    accuracies = [summary["per_condition"].get(cid, {}).get("accuracy") for cid in condition_ids]
    los = [summary["per_condition"].get(cid, {}).get("accuracy_ci_low") for cid in condition_ids]
    his = [summary["per_condition"].get(cid, {}).get("accuracy_ci_high") for cid in condition_ids]

    xs = [length for length, acc in zip(lengths, accuracies, strict=True) if acc is not None]
    ys = [acc for acc in accuracies if acc is not None]
    err_low = [
        (acc - lo)
        for acc, lo in zip(accuracies, los, strict=True)
        if acc is not None and lo is not None
    ]
    err_high = [
        (hi - acc)
        for acc, hi in zip(accuracies, his, strict=True)
        if acc is not None and hi is not None
    ]

    fig, ax = plt.subplots(figsize=(8, 5))
    if xs:
        ax.errorbar(xs, ys, yerr=[err_low, err_high], marker="o", capsize=4)
    ax.set_xscale("log")
    ax.set_xlabel("Context length (estimated tokens)")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1.05)
    title = "Accuracy vs. context length (context rot)"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
