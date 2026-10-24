"""Lab 05 CLI: fixture (default), replay, and live paths.

Lengths that would exceed `preflight.max_input_tokens_per_request` are excluded from the
real run and reported as skipped observations (spec Section 7: "skipped and reported as
skipped, not counted as failures") rather than silently dropped or attempted anyway.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from lab_core.config import load_config
from lab_core.datasets import stratified_subset
from lab_core.execution_mode import ExecutionMode
from lab_core.experiment_runner import ExperimentRunner
from lab_core.fake_client import FakeGroqClient
from lab_core.groq_client import GroqClientAdapter, LiveExecutionNotAllowed
from lab_core.metrics import CostEstimate, PerformanceMetrics, UsageMetrics
from lab_core.preflight import build_preflight_plan, format_plan_report
from lab_core.prompt_builder import build_messages
from lab_core.replay import persist_replay, run_replay
from lab_core.reporting import build_summary, write_full_report
from lab_core.results_writer import Observation, ResultsWriter
from lab_core.tokens import estimate_messages_tokens
from labs.lab05_context_rot.charts import render_length_curve_chart
from labs.lab05_context_rot.conditions import (
    DEFAULT_LENGTHS_TOKENS,
    build_conditions,
    condition_order,
)
from labs.lab05_context_rot.data import facts_to_cases, load_facts, load_filler
from labs.lab05_context_rot.evaluator import evaluate_response
from labs.lab05_context_rot.fixtures import make_fixture_resolver

LAB_ID = "lab05"
PROMPT_TEMPLATE_VERSION = "lab05-v1"


def validate_dataset() -> None:
    facts, _payload = load_facts()
    load_filler(max(DEFAULT_LENGTHS_TOKENS), _tokens_config_for_validation())


def _tokens_config_for_validation():
    from lab_core.config import TokensConfig

    return TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(LAB_ID, help="Lab 05: Context Rot")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--replay", type=Path, default=None)
    parser.add_argument("--allow-prompt-drift", action="store_true")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--profile", choices=["classroom", "full"], default=None)
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument("--yes", action="store_true")
    parser.set_defaults(func=run)


def _skip_observation(
    lab_id, run_id, condition_id, case, repetition, model, execution_mode, reason
):
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
        generation_parameters={},
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        prompt_hash="",
        dataset_version="lab05-facts-v1",
        raw_response=None,
        expected_output=case.expected,
        evaluation_results={},
        usage=UsageMetrics(),
        performance=PerformanceMetrics(),
        cost=CostEstimate(None, reason="skipped"),
        skip_reason=reason,
    )


def run(args: argparse.Namespace) -> None:
    config = load_config(override_path=args.config)
    profile_name = args.profile or config.experiment.default_profile
    profile = config.profiles.classroom if profile_name == "classroom" else config.profiles.full
    max_cases = args.max_cases or profile.max_cases
    repetitions = args.repetitions or profile.repetitions

    facts, _facts_payload = load_facts()
    all_cases = facts_to_cases(facts)
    cases = stratified_subset(all_cases, max_cases, key_fn=lambda c: c.metadata["fact_type"])

    lengths = DEFAULT_LENGTHS_TOKENS
    filler_sentences, _near_miss_noise, _filler_payload = load_filler(max(lengths), config.tokens)
    max_length = config.preflight.max_input_tokens_per_request
    runnable_lengths = [length for length in lengths if length <= max_length]
    skipped_lengths = [length for length in lengths if length not in runnable_lengths]

    conditions = build_conditions(filler_sentences, config.tokens, lengths=runnable_lengths)
    results_dir = Path(config.experiment.results_dir)

    if args.replay is not None:
        result = run_replay(
            source_run_dir=args.replay,
            conditions=conditions,
            cases=cases,
            repetitions=repetitions,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            evaluator=evaluate_response,
            pricing_lookup=config.pricing_for,
            allow_prompt_drift=args.allow_prompt_drift,
        )
        if result.mismatches and not args.allow_prompt_drift:
            print(f"[prompt drift] {len(result.mismatches)} item(s) excluded.")
        run_dir = persist_replay(results_dir, LAB_ID, result, args.replay)
        write_full_report(
            run_dir,
            result.observations,
            condition_order(lengths),
            condition_order(lengths)[0],
            ExecutionMode.REPLAY,
        )
        render_length_curve_chart(
            build_summary(
                result.observations,
                condition_order(lengths),
                condition_order(lengths)[0],
                ExecutionMode.REPLAY,
            ),
            lengths,
            ExecutionMode.REPLAY,
            run_dir / "charts" / "accuracy_vs_length.png",
        )
        print(f"Replay run written to {run_dir}")
        return

    execution_mode = ExecutionMode.LIVE if args.live else ExecutionMode.FIXTURE
    model = config.groq.default_model
    base_generation_params = {
        "temperature": 0.0,
        "max_tokens": 32,
        "reasoning_effort": config.groq.reasoning_effort,
        "include_reasoning": config.groq.include_reasoning,
    }

    if execution_mode is ExecutionMode.LIVE:
        per_request_token_estimates = []
        for condition in conditions:
            components = condition.build_components()
            for case in cases:
                user_input, untrusted = condition.build_user_input(case)
                messages = build_messages(components, user_input, untrusted=untrusted)
                tokens = estimate_messages_tokens([m.as_dict() for m in messages], config.tokens)
                per_request_token_estimates.extend([tokens] * repetitions)
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
        client = FakeGroqClient(
            resolver=make_fixture_resolver(cases, config.tokens), tokens_config=config.tokens
        )

    runner = ExperimentRunner(
        client=client, evaluator=evaluate_response, pricing_lookup=config.pricing_for
    )

    writer = ResultsWriter(results_dir)
    handle = writer.start_run(
        LAB_ID,
        execution_mode,
        run_metadata={
            "model_id": model,
            "profile": profile_name,
            "n_cases": len(cases),
            "repetitions": repetitions,
            "skipped_lengths": skipped_lengths,
        },
    )

    observations = []
    for observation in runner.run(
        lab_id=LAB_ID,
        run_id=handle.run_id,
        conditions=conditions,
        cases=cases,
        repetitions=repetitions,
        model=model,
        base_generation_params=base_generation_params,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        dataset_version="lab05-facts-v1",
        execution_mode=execution_mode,
        seed=args.seed,
    ):
        handle.append_observation(observation)
        observations.append(observation)

    for length in skipped_lengths:
        for case in cases:
            for repetition in range(1, repetitions + 1):
                obs = _skip_observation(
                    LAB_ID,
                    handle.run_id,
                    f"length_{length}",
                    case,
                    repetition,
                    model,
                    execution_mode,
                    reason=f"length {length} exceeds preflight.max_input_tokens_per_request",
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
            "skipped_lengths": skipped_lengths,
        },
        status="completed",
    )

    all_condition_order = condition_order(lengths)
    write_full_report(
        handle.directory, observations, all_condition_order, all_condition_order[0], execution_mode
    )
    summary = build_summary(
        observations, all_condition_order, all_condition_order[0], execution_mode
    )
    render_length_curve_chart(
        summary, lengths, execution_mode, handle.directory / "charts" / "accuracy_vs_length.png"
    )

    print(f"[{execution_mode.banner}]")
    if skipped_lengths:
        print(
            f"[skipped lengths] {skipped_lengths} exceeded preflight.max_input_tokens_per_request"
        )
    print(f"Run written to {handle.directory}")
