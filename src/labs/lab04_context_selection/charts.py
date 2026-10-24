"""Lab 04's priority chart (spec Section 12): selection recall and answer accuracy vs.
budget, across the budget series conditions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.execution_mode import ExecutionMode
from labs.lab04_context_selection.conditions import BUDGET_TOKENS

BUDGET_CONDITIONS = ["budget_200", "budget_500", "budget_1000"]


def render_budget_chart(
    summary: dict[str, Any],
    selection_metrics: dict[str, Any],
    execution_mode: ExecutionMode,
    output_path: Path,
) -> Path:
    budgets = [BUDGET_TOKENS[cid] for cid in BUDGET_CONDITIONS]
    recalls = [
        selection_metrics[cid]["evidence_recall"]["point_estimate"] for cid in BUDGET_CONDITIONS
    ]
    accuracies = [
        summary["per_condition"].get(cid, {}).get("accuracy") or 0.0 for cid in BUDGET_CONDITIONS
    ]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(budgets, recalls, marker="o", label="selection evidence recall")
    ax.plot(budgets, accuracies, marker="s", label="answer accuracy")
    ax.set_xlabel("Token budget")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.05)
    title = "Selection recall & answer accuracy vs. budget"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
