"""Lab 08's priority chart (spec Section 12): three-layer structured-output results by
condition (JSON parse success, schema adherence, semantic accuracy)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.execution_mode import ExecutionMode
from labs.lab08_structured_outputs.conditions import CONDITION_ORDER

LAYERS = ["json_parse_success", "schema_adherent", "semantic_correct"]


def render_three_layer_chart(
    summary: dict[str, Any], execution_mode: ExecutionMode, output_path: Path
) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.25
    x = range(len(CONDITION_ORDER))
    for i, layer in enumerate(LAYERS):
        values = [
            summary["per_condition"]
            .get(cid, {})
            .get("constraint_adherence", {})
            .get(layer, {})
            .get("rate")
            or 0.0
            for cid in CONDITION_ORDER
        ]
        offsets = [xi + (i - 1) * width for xi in x]
        ax.bar(offsets, values, width, label=layer)

    ax.set_xticks(list(x))
    ax.set_xticklabels(CONDITION_ORDER, rotation=20, ha="right")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.05)
    title = "Three-layer structured-output results by mode"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
