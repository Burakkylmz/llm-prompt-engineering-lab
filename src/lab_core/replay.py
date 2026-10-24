"""Re-runs evaluation, statistics, and reporting on a previously recorded run — no client
call, no network (spec Section 5).

Matching key: `(condition_id, case_id, repetition, prompt_hash)`. A mismatched prompt hash
(the prompt template changed since the source run was recorded) is reported, not silently
substituted, unless `allow_prompt_drift=True` — then the item is included anyway and the
whole replay is labeled `drifted`. Replay always writes to a *new* run directory; the source
run is read-only and is never modified (spec Section 5).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from lab_core.config import ModelPricing
from lab_core.execution_mode import ExecutionMode
from lab_core.experiment_runner import Case, Condition, Evaluator
from lab_core.metrics import estimate_cost
from lab_core.prompt_builder import build_messages, compute_prompt_hash
from lab_core.results_writer import Observation, ResultsWriter, new_run_id


@dataclass(frozen=True)
class ReplayMismatch:
    condition_id: str
    case_id: str
    repetition: int
    recorded_prompt_hash: str
    current_prompt_hash: str


@dataclass(frozen=True)
class ReplayResult:
    run_id: str
    observations: list[Observation]
    mismatches: list[ReplayMismatch]
    drifted: bool
    source_run_id: str


def run_replay(
    *,
    source_run_dir: Path,
    conditions: list[Condition],
    cases: list[Case],
    repetitions: int,
    prompt_template_version: str,
    evaluator: Evaluator,
    pricing_lookup: Callable[[str], ModelPricing | None],
    allow_prompt_drift: bool = False,
) -> ReplayResult:
    source_handle = ResultsWriter.load_run(source_run_dir)
    if source_handle.execution_mode not in (
        ExecutionMode.LIVE,
        ExecutionMode.SYNTHETIC_RECORDING_FOR_TESTS,
    ):
        raise ValueError(
            f"Replay source must be a live (or synthetic test recording) run, "
            f"got execution_mode={source_handle.execution_mode.value}"
        )
    recorded = source_handle.read_observations()
    recorded_by_key = {(o.condition_id, o.case_id, o.repetition): o for o in recorded}

    new_run_identifier = new_run_id(ExecutionMode.REPLAY)
    new_observations: list[Observation] = []
    mismatches: list[ReplayMismatch] = []

    for condition in conditions:
        components = condition.build_components()
        for case in cases:
            for repetition in range(1, repetitions + 1):
                key = (condition.condition_id, case.case_id, repetition)
                recorded_obs = recorded_by_key.get(key)
                if recorded_obs is None:
                    continue  # not present in the source run

                messages = build_messages(components, case.input_text)
                current_hash = compute_prompt_hash(prompt_template_version, messages)
                is_mismatch = current_hash != recorded_obs.prompt_hash
                if is_mismatch:
                    mismatches.append(
                        ReplayMismatch(
                            condition_id=condition.condition_id,
                            case_id=case.case_id,
                            repetition=repetition,
                            recorded_prompt_hash=recorded_obs.prompt_hash,
                            current_prompt_hash=current_hash,
                        )
                    )
                    if not allow_prompt_drift:
                        continue

                base = replace(
                    recorded_obs,
                    run_id=new_run_identifier,
                    execution_mode=ExecutionMode.REPLAY.value,
                    source_run_id=recorded_obs.run_id,
                )

                if recorded_obs.raw_response is None:
                    # Original call was skipped or errored; carry that forward unevaluated.
                    new_observations.append(base)
                    continue

                evaluation = evaluator(recorded_obs.raw_response, case)
                cost = estimate_cost(recorded_obs.usage, pricing_lookup(recorded_obs.model_id))
                new_observations.append(
                    replace(
                        base,
                        evaluation_results={
                            "checks": evaluation.checks,
                            "primary_correct": evaluation.primary_correct,
                            "parsed_label": evaluation.parsed_label,
                            "notes": evaluation.notes,
                        },
                        cost=cost,
                    )
                )

    drifted = bool(mismatches) and allow_prompt_drift
    return ReplayResult(
        run_id=new_run_identifier,
        observations=new_observations,
        mismatches=mismatches,
        drifted=drifted,
        source_run_id=source_handle.run_id,
    )


def persist_replay(
    results_dir: Path, lab_id: str, replay_result: ReplayResult, source_run_dir: Path
) -> Path:
    """Writes the replay's observations into a brand-new run directory under `results_dir`."""
    writer = ResultsWriter(results_dir)
    handle = writer.start_run(
        lab_id=lab_id,
        execution_mode=ExecutionMode.REPLAY,
        run_metadata={
            "source_run_id": replay_result.source_run_id,
            "source_run_dir": str(source_run_dir),
            "drifted": replay_result.drifted,
            "mismatch_count": len(replay_result.mismatches),
        },
        run_id=replay_result.run_id,
    )
    for observation in replay_result.observations:
        handle.append_observation(observation)
    handle.write_run_metadata(
        {
            "lab_id": lab_id,
            "run_id": replay_result.run_id,
            "execution_mode": ExecutionMode.REPLAY.value,
            "source_run_id": replay_result.source_run_id,
            "source_run_dir": str(source_run_dir),
            "drifted": replay_result.drifted,
            "mismatch_count": len(replay_result.mismatches),
        },
        status="completed",
    )
    return handle.directory
