"""Lab 06's priority chart (spec Section 12): accuracy by relative position."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.execution_mode import ExecutionMode
from labs.lab06_lost_in_middle.conditions import condition_order


def render_position_curve_chart(
    summary: dict[str, Any],
    positions: list[float],
    execution_mode: ExecutionMode,
    output_path: Path,
) -> Path:
    condition_ids = condition_order(positions)
    accuracies = [summary["per_condition"].get(cid, {}).get("accuracy") for cid in condition_ids]
    los = [summary["per_condition"].get(cid, {}).get("accuracy_ci_low") for cid in condition_ids]
    his = [summary["per_condition"].get(cid, {}).get("accuracy_ci_high") for cid in condition_ids]

    xs = [p for p, acc in zip(positions, accuracies, strict=True) if acc is not None]
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
        ax.errorbar([p * 100 for p in xs], ys, yerr=[err_low, err_high], marker="o", capsize=4)
    ax.set_xlabel("Relative position of target fact (%)")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1.05)
    title = "Accuracy by position (lost-in-the-middle)"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
