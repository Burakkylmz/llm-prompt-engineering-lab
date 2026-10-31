"""Lab 01's priority charts (spec Section 12): instruction adherence per check and condition,
with 95% Wilson CI error bars. Reads the generic per-check rates that
`lab_core.reporting.build_summary` already computes; nothing is recomputed here."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.execution_mode import ExecutionMode

ADHERENCE_CHECKS = [
    "label_in_closed_set",
    "priority_valid",
    "format_compliant",
    "within_length_bound",
    "all_constraints_met",
]
_COLORS = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#333333"]


def render_adherence_chart(
    summary: dict[str, Any],
    condition_ids: list[str],
    execution_mode: ExecutionMode,
    output_path: Path,
) -> Path:
    fig, ax = plt.subplots(figsize=(max(8, 1.3 * len(condition_ids)), 4.8))
    width = 0.8 / len(ADHERENCE_CHECKS)
    for i, check in enumerate(ADHERENCE_CHECKS):
        rates, err_low, err_high = [], [], []
        for cid in condition_ids:
            rate = summary["per_condition"][cid]["constraint_adherence"].get(check)
            if rate is None or rate["rate"] is None:
                # Absent check -> no bar (never drawn as 0%, which would be a fake value).
                rates.append(float("nan"))
                err_low.append(0.0)
                err_high.append(0.0)
                continue
            rates.append(rate["rate"])
            err_low.append(rate["rate"] - rate["ci_low"])
            err_high.append(rate["ci_high"] - rate["rate"])
        offsets = [x - 0.4 + width * (i + 0.5) for x in range(len(condition_ids))]
        ax.bar(
            offsets,
            rates,
            width,
            yerr=[err_low, err_high],
            capsize=2,
            label=check,
            color=_COLORS[i],
        )
    ax.set_xticks(list(range(len(condition_ids))))
    ax.set_xticklabels(condition_ids, rotation=30, ha="right")
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.05)
    title = "Instruction adherence by check (95% Wilson CI)"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
