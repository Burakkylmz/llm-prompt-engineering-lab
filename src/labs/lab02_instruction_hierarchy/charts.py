"""Lab 02's priority chart (spec Section 12): model- vs. system-level attack success rate,
grouped by condition. Reuses the generic `summary["per_condition"][cid]["constraint_adherence"]`
rates that `lab_core.reporting.build_summary` already computes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab_core.execution_mode import ExecutionMode

ATTACK_CONDITIONS = ["A_naive_concat", "B_separated", "C_enforced"]


def render_attack_success_chart(
    summary: dict[str, Any], execution_mode: ExecutionMode, output_path: Path
) -> Path:
    model_rates = []
    system_rates = []
    labels = []
    for cid in ATTACK_CONDITIONS:
        cond = summary["per_condition"].get(cid)
        if cond is None:
            continue
        adherence = cond.get("constraint_adherence", {})
        model_rate = adherence.get("model_level_attack_success", {}).get("rate")
        system_rate = adherence.get("system_level_attack_success", {}).get("rate")
        if model_rate is None and system_rate is None:
            continue
        labels.append(cid)
        model_rates.append(model_rate or 0.0)
        system_rates.append(system_rate or 0.0)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(labels))
    width = 0.35
    ax.bar([i - width / 2 for i in x], model_rates, width, label="model-level", color="#C44E52")
    ax.bar([i + width / 2 for i in x], system_rates, width, label="system-level", color="#4C72B0")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Attack success rate")
    ax.set_ylim(0, 1)
    title = "Model-level vs. system-level attack success"
    if not execution_mode.is_evidence_of_model_behavior:
        title = f"[SIMULATED] {title}"
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
