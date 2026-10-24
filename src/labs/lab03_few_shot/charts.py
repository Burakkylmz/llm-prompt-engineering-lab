"""Lab 03's priority chart (spec Section 12): few-shot quality vs. tokens — one point per
condition, accuracy against mean prompt tokens, so a participant can see directly whether a
condition's extra tokens bought it any accuracy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.execution_mode import ExecutionMode


def render_quality_vs_tokens_chart(
    summary: dict[str, Any], execution_mode: ExecutionMode, output_path: Path
) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    for cid in summary["condition_order"]:
        cond = summary["per_condition"].get(cid, {})
        tokens = cond.get("mean_prompt_tokens")
        accuracy = cond.get("accuracy")
        if tokens is None or accuracy is None:
            continue
        ax.scatter(tokens, accuracy, s=60)
        ax.annotate(cid, (tokens, accuracy), fontsize=8, xytext=(4, 4), textcoords="offset points")

    ax.set_xlabel("Mean prompt tokens (estimated in fixture mode)")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1.05)
    title = "Few-shot quality vs. tokens"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
