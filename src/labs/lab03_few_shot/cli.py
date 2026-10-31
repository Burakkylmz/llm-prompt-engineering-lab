"""Lab 03 CLI: fixture (default), replay, and live paths through one shared pipeline — all
11 conditions evaluate the identical case set (a true paired design, unlike Lab 02)."""

from __future__ import annotations

import argparse
import json
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
from lab_core.reporting import (
    build_reference_comparison,
    build_summary,
    render_reference_comparison_markdown,
    write_full_report,
)
from lab_core.results_writer import ResultsWriter
from lab_core.tokens import estimate_messages_tokens
from labs.lab03_few_shot.charts import render_quality_vs_tokens_chart
from labs.lab03_few_shot.conditions import (
    BASELINE_CONDITION_ID,
    CONDITION_ORDER,
    ORDER_CONDITION_ORDER,
    ORDER_REFERENCE_CONDITION_ID,
    build_conditions,
)
from labs.lab03_few_shot.data import LABELS, load_eval_and_pool
from labs.lab03_few_shot.evaluator import evaluate_response
from labs.lab03_few_shot.fixtures import make_fixture_resolver

LAB_ID = "lab03"
PROMPT_TEMPLATE_VERSION = "lab03-v1"


def validate_dataset() -> None:
    load_eval_and_pool()


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(LAB_ID, help="Lab 03: Few-Shot Example Engineering")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--replay", type=Path, default=None)
    parser.add_argument("--allow-prompt-drift", action="store_true")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--profile", choices=["classroom", "full"], default=None)
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument(
        "--order-effect",
        action="store_true",
        help=(
            "Also run the example-order series (same 4 boundary examples, different order). "
            "Enabled automatically with --profile full."
        ),
    )
    parser.add_argument("--yes", action="store_true")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    config = load_config(override_path=args.config)
    profile_name = args.profile or config.experiment.default_profile
    profile = config.profiles.classroom if profile_name == "classroom" else config.profiles.full
    max_cases = args.max_cases or profile.max_cases
    repetitions = args.repetitions or profile.repetitions

    eval_cases, pool_cases, _eval_payload, _pool_payload = load_eval_and_pool()
    cases = stratified_subset(eval_cases, max_cases, key_fn=lambda c: c.expected["label"])
    include_order_effect = args.order_effect or profile_name == "full"
    # Replay always knows the order conditions; absent ones are simply not in the source run.
    conditions = build_conditions(
        pool_cases, include_order_effect=include_order_effect or args.replay is not None
    )

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
            print(
                f"[prompt drift] {len(result.mismatches)} item(s) excluded due to prompt-hash "
                "mismatch; re-run with --allow-prompt-drift to include them anyway."
            )
        run_dir = persist_replay(results_dir, LAB_ID, result, args.replay)
        _finish_report(run_dir, result.observations, ExecutionMode.REPLAY)
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
                messages = build_messages(components, case.input_text)
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
        client = FakeGroqClient(resolver=make_fixture_resolver(cases), tokens_config=config.tokens)

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
            "order_effect": include_order_effect,
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
        dataset_version="lab03-eval-v1",
        execution_mode=execution_mode,
        seed=args.seed,
    ):
        handle.append_observation(observation)
        observations.append(observation)

    handle.write_run_metadata(
        {
            "lab_id": LAB_ID,
            "run_id": handle.run_id,
            "execution_mode": execution_mode.value,
            "model_id": model,
            "profile": profile_name,
            "n_cases": len(cases),
            "repetitions": repetitions,
            "order_effect": include_order_effect,
        },
        status="completed",
    )
    _finish_report(handle.directory, observations, execution_mode)

    print(f"[{execution_mode.banner}]")
    print(f"Run written to {handle.directory}")


def _finish_report(run_dir: Path, observations: list, execution_mode: ExecutionMode) -> None:
    present = {o.condition_id for o in observations}
    order_ids = [cid for cid in ORDER_CONDITION_ORDER if cid in present]
    condition_order = CONDITION_ORDER + order_ids
    write_full_report(
        run_dir, observations, condition_order, BASELINE_CONDITION_ID, execution_mode, labels=LABELS
    )
    summary = build_summary(
        observations, condition_order, BASELINE_CONDITION_ID, execution_mode, labels=LABELS
    )
    render_quality_vs_tokens_chart(
        summary, execution_mode, run_dir / "charts" / "quality_vs_tokens.png"
    )
    if not order_ids:
        return

    order_comparison = build_reference_comparison(
        observations, ORDER_REFERENCE_CONDITION_ID, order_ids, execution_mode, labels=LABELS
    )
    summary_path = run_dir / "summary.json"
    full_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    full_summary["order_effect_vs_original_order"] = order_comparison
    summary_path.write_text(
        json.dumps(full_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with open(run_dir / "comparison.md", "a", encoding="utf-8") as f:
        f.write(
            render_reference_comparison_markdown(
                "Example order effect (same 4 boundary examples)",
                "Every row uses exactly the same four examples as the reference, in a different "
                "order; nothing else changes. Flips show which cases the order alone moved.",
                order_comparison,
            )
        )


def regenerate_report(run_dir: Path, observations: list, execution_mode: ExecutionMode) -> None:
    """Used by `lab-runner report` (spec Section 12) to rebuild summary, comparison and all of
    this lab's charts from an existing run directory."""
    _finish_report(run_dir, observations, execution_mode)
