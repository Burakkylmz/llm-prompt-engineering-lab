"""The `Observation` record shape (spec Section 12) and the writer that persists it.

Layout: `results/<lab_id>/<timestamp>_<mode>_<shortid>/{run.json, observations.jsonl,
summary.json, comparison.md, charts/*.png}`. `ResultsWriter` never overwrites an existing run
directory, and every observation is appended to `observations.jsonl` as soon as it is
produced (incremental persistence) — a crash after N of M items still leaves N valid,
readable observations plus a `run.json` status of `"partial"`.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lab_core.execution_mode import ExecutionMode
from lab_core.metrics import CostEstimate, PerformanceMetrics, UsageMetrics


@dataclass(frozen=True)
class Observation:
    """One measured execution: a single (condition, case, repetition) triple."""

    experiment_id: str
    lab_id: str
    run_id: str
    condition_id: str
    case_id: str
    repetition: int
    execution_mode: str
    timestamp: str
    model_id: str
    generation_parameters: dict[str, Any]
    prompt_template_version: str
    prompt_hash: str
    dataset_version: str
    raw_response: str | None
    expected_output: dict[str, Any]
    evaluation_results: dict[str, Any]
    usage: UsageMetrics
    performance: PerformanceMetrics
    cost: CostEstimate
    retries: int = 0
    error: str | None = None
    skip_reason: str | None = None
    source_run_id: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_run_id(execution_mode: ExecutionMode, clock: Any = None) -> str:
    now = (clock or datetime.now)(UTC) if clock else datetime.now(UTC)
    timestamp = now.strftime("%Y-%m-%dT%H-%M-%SZ")
    short_id = uuid.uuid4().hex[:6]
    return f"{timestamp}_{execution_mode.value}_{short_id}"


@dataclass
class RunHandle:
    directory: Path
    lab_id: str
    run_id: str
    execution_mode: ExecutionMode
    _observations_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self._observations_path = self.directory / "observations.jsonl"

    def append_observation(self, observation: Observation) -> None:
        with open(self._observations_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(observation.to_json_dict(), ensure_ascii=False) + "\n")

    def write_run_metadata(self, metadata: dict[str, Any], status: str) -> None:
        payload = {**metadata, "status": status}
        with open(self.directory / "run.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def write_summary(self, summary: dict[str, Any]) -> None:
        with open(self.directory / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def write_comparison_markdown(self, markdown: str) -> None:
        (self.directory / "comparison.md").write_text(markdown, encoding="utf-8")

    @property
    def charts_dir(self) -> Path:
        path = self.directory / "charts"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def read_observations(self) -> list[Observation]:
        observations = []
        if not self._observations_path.exists():
            return observations
        with open(self._observations_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                observations.append(
                    Observation(
                        **{
                            **data,
                            "usage": UsageMetrics(**data["usage"]),
                            "performance": PerformanceMetrics(**data["performance"]),
                            "cost": CostEstimate(**data["cost"]),
                        }
                    )
                )
        return observations


class ResultsWriter:
    def __init__(self, results_dir: Path) -> None:
        self._results_dir = results_dir

    def start_run(
        self,
        lab_id: str,
        execution_mode: ExecutionMode,
        run_metadata: dict[str, Any],
        run_id: str | None = None,
    ) -> RunHandle:
        resolved_run_id = run_id or new_run_id(execution_mode)
        run_dir = self._results_dir / lab_id / resolved_run_id
        if run_dir.exists():
            raise FileExistsError(f"Run directory already exists, refusing to overwrite: {run_dir}")
        run_dir.mkdir(parents=True)

        handle = RunHandle(
            directory=run_dir, lab_id=lab_id, run_id=resolved_run_id, execution_mode=execution_mode
        )
        # Always present, even with zero observations (e.g. a replay where every item was
        # excluded for prompt drift) — callers can rely on the file existing, not on at
        # least one append having happened.
        handle._observations_path.touch()
        handle.write_run_metadata(
            {
                "lab_id": lab_id,
                "run_id": resolved_run_id,
                "execution_mode": execution_mode.value,
                **run_metadata,
            },
            status="running",
        )
        return handle

    @staticmethod
    def load_run(run_dir: Path) -> RunHandle:
        run_json_path = run_dir / "run.json"
        if not run_json_path.exists():
            raise FileNotFoundError(f"No run.json found at {run_dir}")
        with open(run_json_path, encoding="utf-8") as f:
            metadata = json.load(f)
        return RunHandle(
            directory=run_dir,
            lab_id=metadata["lab_id"],
            run_id=metadata["run_id"],
            execution_mode=ExecutionMode(metadata["execution_mode"]),
        )
