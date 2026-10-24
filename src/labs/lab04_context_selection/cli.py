"""Lab 04 CLI: fixture (default), replay, and live paths.

Selection-level metrics (spec Section 11 LAB 04: "no LLM needed") are computed directly
from each condition's selector function against the question set, independent of whichever
execution mode is active — they cost nothing and are always real (never SIMULATED),
because they involve no model call at all.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
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
from labs.lab04_context_selection.charts import render_budget_chart
from labs.lab04_context_selection.conditions import (
    BASELINE_CONDITION_ID,
    CONDITION_ORDER,
    build_conditions,
    build_selector_functions,
)
from labs.lab04_context_selection.data import load_corpus, load_questions
from labs.lab04_context_selection.evaluator import evaluate_response
from labs.lab04_context_selection.fixtures import make_fixture_resolver
from labs.lab04_context_selection.selection_metrics import compute_selection_metrics

LAB_ID = "lab04"
PROMPT_TEMPLATE_VERSION = "lab04-v1"


def validate_dataset() -> None:
    load_corpus()
    load_questions()


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        LAB_ID, help="Lab 04: Context Selection, Budget, Ordering & Freshness"
    )
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


def _selection_metrics_dict(cases, corpus, tokens_config) -> dict:
    corpus_by_id = {doc.doc_id: doc for doc in corpus}
    selectors = build_selector_functions(corpus, tokens_config)
    result = {}
    for condition_id in CONDITION_ORDER:
        metrics = compute_selection_metrics(cases, selectors[condition_id], corpus_by_id)
        result[condition_id] = {
            "evidence_recall": asdict(metrics.evidence_recall),
            "evidence_precision": asdict(metrics.evidence_precision),
            "stale_inclusion_rate": asdict(metrics.stale_inclusion_rate),
            "n_questions": metrics.n_questions,
        }
    return result


def _render_selection_metrics_markdown(selection_metrics: dict) -> str:
    lines = ["\n## Selection-level metrics (no LLM call; always real, never simulated)\n"]
    lines.append("| Condition | Evidence recall | Evidence precision | Stale-doc inclusion rate |")
    lines.append("|---|---|---|---|")
    for cid in CONDITION_ORDER:
        m = selection_metrics[cid]
        lines.append(
            f"| {cid} | {m['evidence_recall']['point_estimate']:.2%} | "
            f"{m['evidence_precision']['point_estimate']:.2%} | "
            f"{m['stale_inclusion_rate']['point_estimate']:.2%} |"
        )
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> None:
    config = load_config(override_path=args.config)
    profile_name = args.profile or config.experiment.default_profile
    profile = config.profiles.classroom if profile_name == "classroom" else config.profiles.full
    max_cases = args.max_cases or profile.max_cases
    repetitions = args.repetitions or profile.repetitions

    corpus, _corpus_payload = load_corpus()
    all_questions, _q_payload = load_questions()
    cases = stratified_subset(all_questions, max_cases, key_fn=lambda c: c.metadata["topic"])
    conditions = build_conditions(corpus, config.tokens)

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
        _finish_report(
            run_dir, result.observations, ExecutionMode.REPLAY, cases, corpus, config.tokens
        )
        print(f"Replay run written to {run_dir}")
        return

    execution_mode = ExecutionMode.LIVE if args.live else ExecutionMode.FIXTURE
    model = config.groq.default_model
    base_generation_params = {
        "temperature": 0.0,
        "max_tokens": 64,
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
        dataset_version="lab04-questions-v1",
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
        },
        status="completed",
    )
    _finish_report(handle.directory, observations, execution_mode, cases, corpus, config.tokens)

    print(f"[{execution_mode.banner}]")
    print(f"Run written to {handle.directory}")


def _finish_report(
    run_dir: Path, observations, execution_mode, cases, corpus, tokens_config
) -> None:
    write_full_report(run_dir, observations, CONDITION_ORDER, BASELINE_CONDITION_ID, execution_mode)
    summary = build_summary(observations, CONDITION_ORDER, BASELINE_CONDITION_ID, execution_mode)

    selection_metrics = _selection_metrics_dict(cases, corpus, tokens_config)
    summary["selection_metrics"] = selection_metrics
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open(run_dir / "comparison.md", "a", encoding="utf-8") as f:
        f.write(_render_selection_metrics_markdown(selection_metrics))

    render_budget_chart(
        summary,
        selection_metrics,
        execution_mode,
        run_dir / "charts" / "budget_vs_recall_accuracy.png",
    )
