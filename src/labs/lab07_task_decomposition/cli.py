"""Lab 07 CLI: fixture (default), replay, and live paths.

Bypasses `ExperimentRunner` (spec's multi-call conditions don't fit "one call per trial");
see `docs/decisions.md`. Replay here is a lightweight, Lab-07-specific re-evaluation of
previously recorded raw step responses (`orchestration.reconstruct_from_raw`) — it does not
reuse `lab_core.replay`'s prompt-hash drift detection, since a multi-call trial has no
single prompt to hash.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from lab_core.config import load_config
from lab_core.datasets import stratified_subset
from lab_core.execution_mode import ExecutionMode
from lab_core.fake_client import FakeGroqClient
from lab_core.groq_client import GroqClientAdapter, LiveExecutionNotAllowed
from lab_core.metrics import PerformanceMetrics, estimate_cost
from lab_core.preflight import build_preflight_plan, format_plan_report
from lab_core.reporting import build_summary, write_full_report
from lab_core.results_writer import Observation, ResultsWriter
from lab_core.tokens import estimate_tokens
from labs.lab07_task_decomposition.charts import render_accuracy_vs_cost_chart
from labs.lab07_task_decomposition.data import load_cases
from labs.lab07_task_decomposition.evaluator import evaluate_result
from labs.lab07_task_decomposition.fixtures import make_fixture_resolver
from labs.lab07_task_decomposition.orchestration import (
    STEP_SEPARATOR,
    reconstruct_from_raw,
    run_direct_answer,
    run_multi_call_decomposition,
    run_structured_single_call,
)

LAB_ID = "lab07"
PROMPT_TEMPLATE_VERSION = "lab07-v1"

PRIMARY_CONDITION_ORDER = [
    "direct_answer",
    "single_call_structured",
    "multi_call_decomposition",
    "multi_call_validated",
]
REASONING_SWEEP_ORDER = ["reasoning_low", "reasoning_medium", "reasoning_high"]
CONDITION_ORDER = PRIMARY_CONDITION_ORDER + REASONING_SWEEP_ORDER
BASELINE_CONDITION_ID = "direct_answer"


def validate_dataset() -> None:
    load_cases()


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(LAB_ID, help="Lab 07: Reasoning Guidance & Task Decomposition")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--replay", type=Path, default=None)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--profile", choices=["classroom", "full"], default=None)
    parser.add_argument("--yes", action="store_true")
    parser.set_defaults(func=run)


def _run_condition(condition_id: str, client, case, model: str, base_params: dict):
    if condition_id == "direct_answer":
        return run_direct_answer(client, case, model, base_params)
    if condition_id == "single_call_structured":
        return run_structured_single_call(client, case, model, base_params)
    if condition_id == "multi_call_decomposition":
        return run_multi_call_decomposition(client, case, model, base_params, validate=False)
    if condition_id == "multi_call_validated":
        return run_multi_call_decomposition(client, case, model, base_params, validate=True)
    if condition_id in ("reasoning_low", "reasoning_medium", "reasoning_high"):
        effort = condition_id.removeprefix("reasoning_")
        params = {**base_params, "reasoning_effort": effort}
        return run_direct_answer(client, case, model, params)
    raise ValueError(f"Unknown condition_id: {condition_id}")


def _build_observation(
    lab_id,
    run_id,
    condition_id,
    case,
    repetition,
    model,
    generation_params,
    execution_mode,
    result,
    pricing_lookup,
):
    prompt_hash = hashlib.sha256(
        f"{condition_id}:{case.input_text}:{PROMPT_TEMPLATE_VERSION}".encode()
    ).hexdigest()
    cost = estimate_cost(result.total_usage, pricing_lookup(model))
    checks_result = evaluate_result(result, case)
    return Observation(
        experiment_id=f"{lab_id}:{run_id}",
        lab_id=lab_id,
        run_id=run_id,
        condition_id=condition_id,
        case_id=case.case_id,
        repetition=repetition,
        execution_mode=execution_mode.value,
        timestamp=datetime.now(UTC).isoformat(),
        model_id=model,
        generation_parameters=generation_params,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        prompt_hash=prompt_hash,
        dataset_version="lab07-cases-v1",
        raw_response=STEP_SEPARATOR.join(result.raw_responses) if result.raw_responses else None,
        expected_output=case.expected,
        evaluation_results={
            "checks": checks_result.checks,
            "primary_correct": checks_result.primary_correct,
            "parsed_label": checks_result.parsed_label,
            "notes": checks_result.notes,
        },
        usage=result.total_usage,
        performance=PerformanceMetrics(client_elapsed_ms=result.total_latency_ms),
        cost=cost,
    )


def _estimate_tokens_for_condition(condition_id: str, case, tokens_config) -> int:
    from labs.lab07_task_decomposition import prompts as P

    base = estimate_tokens(case.input_text, tokens_config)
    if condition_id in ("direct_answer", "reasoning_low", "reasoning_medium", "reasoning_high"):
        return base + estimate_tokens(P.DIRECT_SYSTEM, tokens_config)
    if condition_id == "single_call_structured":
        return base + estimate_tokens(P.STRUCTURED_SINGLE_CALL_SYSTEM, tokens_config)
    # Multi-call: 4 calls, each roughly case-description-sized context plus its own system prompt.
    system_texts = [
        P.EXTRACT_FACTS_SYSTEM,
        P.DETERMINE_RULES_SYSTEM,
        P.EVALUATE_RULES_SYSTEM,
        P.DECIDE_SYSTEM,
    ]
    total = sum(base + estimate_tokens(t, tokens_config) for t in system_texts)
    if condition_id == "multi_call_validated":
        total += base + estimate_tokens(P.EVALUATE_RULES_SYSTEM, tokens_config)  # possible re-ask
    return total


def run(args: argparse.Namespace) -> None:
    config = load_config(override_path=args.config)
    profile_name = args.profile or config.experiment.default_profile
    profile = config.profiles.classroom if profile_name == "classroom" else config.profiles.full
    max_cases = args.max_cases or profile.max_cases
    repetitions = args.repetitions or profile.repetitions

    all_cases, _payload = load_cases()
    cases = stratified_subset(all_cases, max_cases, key_fn=lambda c: c.expected["gold_decision"])

    results_dir = Path(config.experiment.results_dir)
    model = config.groq.default_model
    base_params = {
        "temperature": 0.0,
        "max_tokens": 64,
        "reasoning_effort": config.groq.reasoning_effort,
        "include_reasoning": config.groq.include_reasoning,
    }

    if args.replay is not None:
        source_handle = ResultsWriter.load_run(args.replay)
        if source_handle.execution_mode not in (
            ExecutionMode.LIVE,
            ExecutionMode.SYNTHETIC_RECORDING_FOR_TESTS,
        ):
            print(
                f"[replay blocked] source run execution_mode={source_handle.execution_mode.value} "
                "is not live/synthetic-recording"
            )
            return
        recorded = source_handle.read_observations()
        new_run_id = _new_replay_run_id()
        writer = ResultsWriter(results_dir)
        handle = writer.start_run(
            LAB_ID,
            ExecutionMode.REPLAY,
            run_metadata={
                "source_run_id": source_handle.run_id,
                "source_run_dir": str(args.replay),
            },
            run_id=new_run_id,
        )
        observations = []
        cases_by_id = {c.case_id: c for c in all_cases}
        for obs in recorded:
            case = cases_by_id.get(obs.case_id)
            if case is None or obs.raw_response is None:
                continue
            raw_responses = obs.raw_response.split(STEP_SEPARATOR)
            result = reconstruct_from_raw(obs.condition_id, raw_responses)
            new_obs = _build_observation(
                LAB_ID,
                new_run_id,
                obs.condition_id,
                case,
                obs.repetition,
                obs.model_id,
                obs.generation_parameters,
                ExecutionMode.REPLAY,
                result,
                config.pricing_for,
            )
            new_obs = dataclasses.replace(new_obs, source_run_id=source_handle.run_id)
            handle.append_observation(new_obs)
            observations.append(new_obs)
        handle.write_run_metadata(
            {
                "lab_id": LAB_ID,
                "run_id": new_run_id,
                "execution_mode": ExecutionMode.REPLAY.value,
                "source_run_id": source_handle.run_id,
            },
            status="completed",
        )
        _finish_report(handle.directory, observations, ExecutionMode.REPLAY, cases, config.tokens)
        print(f"Replay run written to {handle.directory}")
        return

    execution_mode = ExecutionMode.LIVE if args.live else ExecutionMode.FIXTURE

    if execution_mode is ExecutionMode.LIVE:
        per_request_token_estimates = []
        for condition_id in CONDITION_ORDER:
            for case in cases:
                per_request_token_estimates.append(
                    _estimate_tokens_for_condition(condition_id, case, config.tokens)
                )
        per_request_token_estimates = [
            t for t in per_request_token_estimates for _ in range(repetitions)
        ]
        plan = build_preflight_plan(
            per_request_token_estimates=per_request_token_estimates,
            preflight_config=config.preflight,
            pricing=config.pricing_for(model),
        )
        print(format_plan_report(plan))
        if plan.should_abort:
            print("[live execution blocked] pre-flight plan exceeds configured limits; aborting.")
            return
        if plan.requires_confirmation and not args.yes:
            print("[live execution blocked] re-run with --yes to confirm this run size.")
            return
        try:
            client = GroqClientAdapter(
                live_authorized=args.live and config.execution.live_api_enabled,
                request_timeout_seconds=config.groq.request_timeout_seconds,
            )
        except LiveExecutionNotAllowed as exc:
            print(f"[live execution blocked] {exc}")
            return
        print(f"[COST WARNING] {config.execution.cost_warning_message}")
    else:
        client = FakeGroqClient(resolver=make_fixture_resolver(cases), tokens_config=config.tokens)

    writer = ResultsWriter(results_dir)
    handle = writer.start_run(
        LAB_ID,
        execution_mode,
        run_metadata={
            "model_id": model,
            "profile": profile_name,
            "n_cases": len(cases),
            "repetitions": repetitions,
        },
    )

    observations = []
    for condition_id in CONDITION_ORDER:
        generation_params = dict(base_params)
        if condition_id in ("reasoning_low", "reasoning_medium", "reasoning_high"):
            generation_params["reasoning_effort"] = condition_id.removeprefix("reasoning_")
        for case in cases:
            for repetition in range(1, repetitions + 1):
                result = _run_condition(condition_id, client, case, model, generation_params)
                obs = _build_observation(
                    LAB_ID,
                    handle.run_id,
                    condition_id,
                    case,
                    repetition,
                    model,
                    generation_params,
                    execution_mode,
                    result,
                    config.pricing_for,
                )
                handle.append_observation(obs)
                observations.append(obs)

    handle.write_run_metadata(
        {
            "lab_id": LAB_ID,
            "run_id": handle.run_id,
            "execution_mode": execution_mode.value,
            "model_id": model,
            "profile": profile_name,
            "n_cases": len(cases),
            "repetitions": repetitions,
        },
        status="completed",
    )
    _finish_report(handle.directory, observations, execution_mode, cases, config.tokens)

    print(f"[{execution_mode.banner}]")
    print(f"Run written to {handle.directory}")


def _new_replay_run_id() -> str:
    from lab_core.results_writer import new_run_id

    return new_run_id(ExecutionMode.REPLAY)


def _finish_report(
    run_dir: Path,
    observations: list[Observation],
    execution_mode: ExecutionMode,
    cases,
    tokens_config,
) -> None:
    write_full_report(run_dir, observations, CONDITION_ORDER, BASELINE_CONDITION_ID, execution_mode)
    summary = build_summary(observations, CONDITION_ORDER, BASELINE_CONDITION_ID, execution_mode)

    call_counts: dict[str, float] = {}
    for cid in PRIMARY_CONDITION_ORDER:
        notes_counts = [
            o.evaluation_results.get("notes", {}).get("api_call_count")
            for o in observations
            if o.condition_id == cid
            and o.evaluation_results.get("notes", {}).get("api_call_count") is not None
        ]
        if notes_counts:
            call_counts[cid] = sum(notes_counts) / len(notes_counts)

    render_accuracy_vs_cost_chart(
        summary, call_counts, execution_mode, run_dir / "charts" / "accuracy_vs_cost.png"
    )
