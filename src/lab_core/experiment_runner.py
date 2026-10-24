"""Executes conditions x cases x repetitions against a `ChatClient` (real, fake, or a
replay-mode stand-in) and yields `Observation`s (spec Section 8).

Paired design is structural here, not incidental: `cases` is one fixed list shared by every
condition in a run. Execution order is seeded and shuffled across the full cross product so
time-of-run effects (API warm-up, rate-limit windows) never correlate with any one condition
(spec Section 8's "seeded counterbalanced ordering").
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from lab_core.config import ModelPricing
from lab_core.evaluation import EvaluationResult
from lab_core.execution_mode import ExecutionMode
from lab_core.groq_client import (
    ChatClient,
    CompletionRequest,
    UnsupportedCapabilityError,
)
from lab_core.metrics import CostEstimate, PerformanceMetrics, UsageMetrics, estimate_cost
from lab_core.prompt_builder import PromptComponents, build_messages, compute_prompt_hash
from lab_core.results_writer import Observation


@dataclass(frozen=True)
class Case:
    case_id: str
    input_text: str
    expected: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Condition:
    condition_id: str
    build_components: Callable[[], PromptComponents]
    generation_overrides: dict[str, Any] = field(default_factory=dict)


Evaluator = Callable[[str, Case], EvaluationResult]


class ExperimentRunner:
    def __init__(
        self,
        client: ChatClient,
        evaluator: Evaluator,
        pricing_lookup: Callable[[str], ModelPricing | None],
    ) -> None:
        self._client = client
        self._evaluator = evaluator
        self._pricing_lookup = pricing_lookup

    def run(
        self,
        *,
        lab_id: str,
        run_id: str,
        conditions: list[Condition],
        cases: list[Case],
        repetitions: int,
        model: str,
        base_generation_params: dict[str, Any],
        prompt_template_version: str,
        dataset_version: str,
        execution_mode: ExecutionMode,
        seed: int,
    ) -> Iterator[Observation]:
        items = [
            (condition, case, repetition)
            for condition in conditions
            for case in cases
            for repetition in range(1, repetitions + 1)
        ]
        order = list(range(len(items)))
        random.Random(seed).shuffle(order)

        for idx in order:
            condition, case, repetition = items[idx]
            yield self._execute_one(
                lab_id=lab_id,
                run_id=run_id,
                condition=condition,
                case=case,
                repetition=repetition,
                model=model,
                base_generation_params=base_generation_params,
                prompt_template_version=prompt_template_version,
                dataset_version=dataset_version,
                execution_mode=execution_mode,
            )

    def _execute_one(
        self,
        *,
        lab_id: str,
        run_id: str,
        condition: Condition,
        case: Case,
        repetition: int,
        model: str,
        base_generation_params: dict[str, Any],
        prompt_template_version: str,
        dataset_version: str,
        execution_mode: ExecutionMode,
    ) -> Observation:
        components = condition.build_components()
        messages = build_messages(components, case.input_text)
        prompt_hash = compute_prompt_hash(prompt_template_version, messages)
        generation_params = {**base_generation_params, **condition.generation_overrides}

        common = {
            "experiment_id": f"{lab_id}:{run_id}",
            "lab_id": lab_id,
            "run_id": run_id,
            "condition_id": condition.condition_id,
            "case_id": case.case_id,
            "repetition": repetition,
            "execution_mode": execution_mode.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "model_id": model,
            "generation_parameters": generation_params,
            "prompt_template_version": prompt_template_version,
            "prompt_hash": prompt_hash,
            "dataset_version": dataset_version,
            "expected_output": case.expected,
        }

        request = CompletionRequest(
            messages=messages,
            model=model,
            temperature=generation_params.get("temperature", 0.0),
            max_tokens=generation_params.get("max_tokens"),
            reasoning_effort=generation_params.get("reasoning_effort"),
            include_reasoning=generation_params.get("include_reasoning", False),
            response_format=generation_params.get("response_format"),
        )

        try:
            result = self._client.complete(request)
        except UnsupportedCapabilityError as exc:
            return Observation(
                **common,
                raw_response=None,
                evaluation_results={},
                usage=UsageMetrics(),
                performance=PerformanceMetrics(),
                cost=CostEstimate(None, reason="skipped: unsupported capability"),
                skip_reason=f"unsupported:{exc}",
            )
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any client failure must still persist a partial observation
            return Observation(
                **common,
                raw_response=None,
                evaluation_results={},
                usage=UsageMetrics(),
                performance=PerformanceMetrics(),
                cost=CostEstimate(None, reason="no response: call failed"),
                error=str(exc),
            )

        evaluation = self._evaluator(result.content, case)
        cost = estimate_cost(result.usage, self._pricing_lookup(model))

        return Observation(
            **common,
            raw_response=result.content,
            evaluation_results={
                "checks": evaluation.checks,
                "primary_correct": evaluation.primary_correct,
                "parsed_label": evaluation.parsed_label,
                "notes": evaluation.notes,
            },
            usage=result.usage,
            performance=result.performance,
            cost=cost,
        )
