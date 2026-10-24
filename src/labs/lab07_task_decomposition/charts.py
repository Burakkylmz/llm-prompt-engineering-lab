"""Lab 07's priority chart (spec Section 12): decomposition accuracy vs. cost (mean API
call count per trial, as a free proxy when verified pricing is unavailable)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.execution_mode import ExecutionMode

PRIMARY_CONDITIONS = [
    "direct_answer",
    "single_call_structured",
    "multi_call_decomposition",
    "multi_call_validated",
]


def render_accuracy_vs_cost_chart(
    summary: dict[str, Any],
    call_counts: dict[str, float],
    execution_mode: ExecutionMode,
    output_path: Path,
) -> Path:
    xs, ys, labels = [], [], []
    for cid in PRIMARY_CONDITIONS:
        cond = summary["per_condition"].get(cid)
        if cond is None or cond.get("accuracy") is None:
            continue
        xs.append(call_counts.get(cid, 1))
        ys.append(cond["accuracy"])
        labels.append(cid)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(xs, ys, s=80)
    for x, y, label in zip(xs, ys, labels, strict=True):
        ax.annotate(label, (x, y), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("Mean API calls per trial (cost proxy)")
    ax.set_ylabel("End-to-end accuracy")
    ax.set_ylim(0, 1.05)
    title = "Decomposition accuracy vs. cost"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
