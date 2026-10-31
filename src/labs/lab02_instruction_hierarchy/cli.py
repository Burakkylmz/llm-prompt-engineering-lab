"""Lab 02 CLI: fixture (default), replay, and live paths.

Orchestrates several `ExperimentRunner.run()` calls (one per evaluator-variant x case-set
combination) into a single run directory, because this lab's conditions are not all
evaluated the same way or on the same case set (spec Section 11 LAB 02) — see
`docs/experiment-methodology.md` for why.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lab_core.config import load_config
from lab_core.datasets import stratified_subset
from lab_core.execution_mode import ExecutionMode
from lab_core.experiment_runner import ExperimentRunner
from lab_core.fake_client import FakeGroqClient
from lab_core.groq_client import GroqClientAdapter, LiveExecutionNotAllowed
from lab_core.preflight import build_preflight_plan, format_plan_report
from lab_core.prompt_builder import build_messages
from lab_core.replay import persist_replay, run_replay
from lab_core.reporting import build_summary, write_full_report
from lab_core.results_writer import ResultsWriter
from lab_core.tokens import estimate_messages_tokens
from labs.lab02_instruction_hierarchy.charts import render_attack_success_chart
from labs.lab02_instruction_hierarchy.conditions import (
    BASELINE_CONDITION_ID,
    CONDITION_ORDER,
    build_conditions,
)
from labs.lab02_instruction_hierarchy.data import load_cases
from labs.lab02_instruction_hierarchy.evaluator import (
    evaluate_response,
    evaluate_response_direct_conflict,
    evaluate_response_enforced,
)
from labs.lab02_instruction_hierarchy.fixtures import make_fixture_resolver

LAB_ID = "lab02"
PROMPT_TEMPLATE_VERSION = "lab02-v1"


def validate_dataset() -> None:
    load_cases()


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(LAB_ID, help="Lab 02: Instruction Hierarchy & Untrusted Content")
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


def _condition_groups(conditions_by_id: dict):
    """Maps each (evaluator, case-set-kind) group to the condition_ids that belong to it."""
    return [
        (evaluate_response, "clean", ["baseline"]),
        (evaluate_response, "injection", ["A_naive_concat", "B_separated"]),
        (evaluate_response, "benign", ["A_naive_concat_benign", "B_separated_benign"]),
        (evaluate_response_enforced, "injection", ["C_enforced"]),
        (evaluate_response_enforced, "benign", ["C_enforced_benign"]),
        (evaluate_response_direct_conflict, "clean", ["D_direct_conflict"]),
    ]


def run(args: argparse.Namespace) -> None:
    config = load_config(override_path=args.config)
    profile_name = args.profile or config.experiment.default_profile
    profile = config.profiles.classroom if profile_name == "classroom" else config.profiles.full
    max_cases = args.max_cases or profile.max_cases
    repetitions = args.repetitions or profile.repetitions

    clean_cases, injection_cases, benign_cases, _payload = load_cases()
    clean_cases = stratified_subset(
        clean_cases, max_cases, key_fn=lambda c: c.expected["gold_decision"]
    )
    injection_cases = stratified_subset(
        injection_cases, max_cases, key_fn=lambda c: c.metadata["untrusted"]["injection_type"]
    )
    benign_cases = stratified_subset(benign_cases, max_cases, key_fn=lambda c: c.case_id)
    case_sets = {"clean": clean_cases, "injection": injection_cases, "benign": benign_cases}

    conditions = {c.condition_id: c for c in build_conditions()}
    results_dir = Path(config.experiment.results_dir)

    if args.replay is not None:
        all_observations = []
        all_mismatches = []
        for evaluator, case_kind, condition_ids in _condition_groups(conditions):
            result = run_replay(
                source_run_dir=args.replay,
                conditions=[conditions[cid] for cid in condition_ids],
                cases=case_sets[case_kind],
                repetitions=repetitions,
                prompt_template_version=PROMPT_TEMPLATE_VERSION,
                evaluator=evaluator,
                pricing_lookup=config.pricing_for,
                allow_prompt_drift=args.allow_prompt_drift,
            )
            all_observations.extend(result.observations)
            all_mismatches.extend(result.mismatches)
            run_id = result.run_id
            source_run_id = result.source_run_id
        if all_mismatches and not args.allow_prompt_drift:
            print(
                f"[prompt drift] {len(all_mismatches)} item(s) excluded due to prompt-hash "
                "mismatch; re-run with --allow-prompt-drift to include them anyway."
            )
        from lab_core.replay import ReplayResult

        combined = ReplayResult(
            run_id=run_id,
            observations=all_observations,
            mismatches=all_mismatches,
            drifted=bool(all_mismatches) and args.allow_prompt_drift,
            source_run_id=source_run_id,
        )
        run_dir = persist_replay(results_dir, LAB_ID, combined, args.replay)
        _finish_report(run_dir, all_observations, ExecutionMode.REPLAY)
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
        for _evaluator, case_kind, condition_ids in _condition_groups(conditions):
            for cid in condition_ids:
                condition = conditions[cid]
                components = condition.build_components()
                for case in case_sets[case_kind]:
                    user_input, untrusted = (
                        condition.build_user_input or (lambda c: (c.input_text, ()))
                    )(case)
                    messages = build_messages(components, user_input, untrusted=untrusted)
                    tokens = estimate_messages_tokens(
                        [m.as_dict() for m in messages], config.tokens
                    )
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
            resolver=make_fixture_resolver(clean_cases + injection_cases + benign_cases),
            tokens_config=config.tokens,
        )

    writer = ResultsWriter(results_dir)
    handle = writer.start_run(
        LAB_ID,
        execution_mode,
        run_metadata={"model_id": model, "profile": profile_name, "repetitions": repetitions},
    )

    all_observations = []
    for evaluator, case_kind, condition_ids in _condition_groups(conditions):
        runner = ExperimentRunner(
            client=client, evaluator=evaluator, pricing_lookup=config.pricing_for
        )
        for observation in runner.run(
            lab_id=LAB_ID,
            run_id=handle.run_id,
            conditions=[conditions[cid] for cid in condition_ids],
            cases=case_sets[case_kind],
            repetitions=repetitions,
            model=model,
            base_generation_params=base_generation_params,
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            dataset_version="lab02-eval-v1",
            execution_mode=execution_mode,
            seed=args.seed,
        ):
            handle.append_observation(observation)
            all_observations.append(observation)

    handle.write_run_metadata(
        {
            "lab_id": LAB_ID,
            "run_id": handle.run_id,
            "execution_mode": execution_mode.value,
            "model_id": model,
            "profile": profile_name,
            "repetitions": repetitions,
        },
        status="completed",
    )
    _finish_report(handle.directory, all_observations, execution_mode)

    print(f"[{execution_mode.banner}]")
    print(f"Run written to {handle.directory}")


def _finish_report(run_dir: Path, observations: list, execution_mode: ExecutionMode) -> None:
    write_full_report(run_dir, observations, CONDITION_ORDER, BASELINE_CONDITION_ID, execution_mode)
    summary = build_summary(observations, CONDITION_ORDER, BASELINE_CONDITION_ID, execution_mode)
    render_attack_success_chart(summary, execution_mode, run_dir / "charts" / "attack_success.png")


def regenerate_report(run_dir: Path, observations: list, execution_mode: ExecutionMode) -> None:
    """Used by `lab-runner report` (spec Section 12) to rebuild summary, comparison and all of
    this lab's charts from an existing run directory."""
    _finish_report(run_dir, observations, execution_mode)
