from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.evaluation import EvaluationResult, closed_set_match
from lab_core.execution_mode import ExecutionMode
from lab_core.experiment_runner import Case, Condition, ExperimentRunner
from lab_core.fake_client import FakeGroqClient
from lab_core.prompt_builder import PromptComponents

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def _evaluator(content: str, case: Case) -> EvaluationResult:
    predicted = content.strip()
    gold = case.expected["label"]
    correct = closed_set_match(predicted, gold)
    return EvaluationResult(
        checks={"label_in_set": True}, primary_correct=correct, parsed_label=predicted
    )


def _resolver_returns_gold(request):
    # Cheat resolver for pipeline testing: echoes back whatever the (fixture-mode-only)
    # test wants, independent of condition — real fixture resolvers are per-lab.
    return "billing"


def _make_runner():
    client = FakeGroqClient(resolver=_resolver_returns_gold, tokens_config=TOKENS_CFG)
    return client, ExperimentRunner(
        client=client, evaluator=_evaluator, pricing_lookup=lambda _m: None
    )


def test_runner_produces_one_observation_per_condition_case_repetition():
    client, runner = _make_runner()
    conditions = [
        Condition("baseline", lambda: PromptComponents(instruction="Siniflandir.")),
        Condition(
            "A_context",
            lambda: PromptComponents(instruction="Siniflandir.", constraints="Sadece etiket don."),
        ),
    ]
    cases = [
        Case("c1", "mesaj 1", {"label": "billing"}),
        Case("c2", "mesaj 2", {"label": "billing"}),
    ]

    observations = list(
        runner.run(
            lab_id="lab01",
            run_id="run1",
            conditions=conditions,
            cases=cases,
            repetitions=2,
            model="openai/gpt-oss-20b",
            base_generation_params={"temperature": 0.0},
            prompt_template_version="v1",
            dataset_version="v1",
            execution_mode=ExecutionMode.FIXTURE,
            seed=42,
        )
    )
    assert len(observations) == 2 * 2 * 2  # conditions x cases x repetitions
    assert all(o.evaluation_results.get("primary_correct") is True for o in observations)


def test_runner_execution_order_is_deterministic_for_fixed_seed():
    conditions = [Condition("baseline", lambda: PromptComponents(instruction="x"))]
    cases = [Case(f"c{i}", f"msg{i}", {"label": "billing"}) for i in range(5)]

    def run_once():
        client, runner = _make_runner()
        return [
            o.case_id
            for o in runner.run(
                lab_id="lab01",
                run_id="run1",
                conditions=conditions,
                cases=cases,
                repetitions=1,
                model="m",
                base_generation_params={},
                prompt_template_version="v1",
                dataset_version="v1",
                execution_mode=ExecutionMode.FIXTURE,
                seed=7,
            )
        ]

    assert run_once() == run_once()


def test_runner_paired_design_same_cases_across_conditions():
    conditions = [
        Condition("baseline", lambda: PromptComponents(instruction="x")),
        Condition("treatment", lambda: PromptComponents(instruction="y")),
    ]
    cases = [Case("c1", "m1", {"label": "billing"}), Case("c2", "m2", {"label": "billing"})]
    client, runner = _make_runner()
    observations = list(
        runner.run(
            lab_id="lab01",
            run_id="run1",
            conditions=conditions,
            cases=cases,
            repetitions=1,
            model="m",
            base_generation_params={},
            prompt_template_version="v1",
            dataset_version="v1",
            execution_mode=ExecutionMode.FIXTURE,
            seed=1,
        )
    )
    cases_per_condition = {}
    for o in observations:
        cases_per_condition.setdefault(o.condition_id, set()).add(o.case_id)
    assert cases_per_condition["baseline"] == cases_per_condition["treatment"]


def test_unsupported_capability_recorded_as_skip_not_failure():
    from lab_core.groq_client import UnsupportedCapabilityError

    class _RaisingClient:
        def complete(self, request):
            raise UnsupportedCapabilityError("response_format not supported")

    runner = ExperimentRunner(
        client=_RaisingClient(), evaluator=_evaluator, pricing_lookup=lambda _m: None
    )
    conditions = [Condition("baseline", lambda: PromptComponents(instruction="x"))]
    cases = [Case("c1", "m1", {"label": "billing"})]
    observations = list(
        runner.run(
            lab_id="lab01",
            run_id="run1",
            conditions=conditions,
            cases=cases,
            repetitions=1,
            model="m",
            base_generation_params={},
            prompt_template_version="v1",
            dataset_version="v1",
            execution_mode=ExecutionMode.FIXTURE,
            seed=1,
        )
    )
    assert len(observations) == 1
    assert observations[0].skip_reason is not None
    assert observations[0].error is None


def test_per_case_untrusted_content_via_build_user_input():
    from lab_core.prompt_builder import UntrustedBlock

    def _build_user_input(case: Case):
        return case.input_text, (
            UntrustedBlock(source="ek_belge", text=case.metadata["attachment"]),
        )

    client, runner = _make_runner()
    conditions = [
        Condition(
            "with_attachment",
            lambda: PromptComponents(instruction="x"),
            build_user_input=_build_user_input,
        )
    ]
    cases = [
        Case("c1", "musteri mesaji", {"label": "billing"}, metadata={"attachment": "ek metin"})
    ]
    observations = list(
        runner.run(
            lab_id="lab01",
            run_id="run1",
            conditions=conditions,
            cases=cases,
            repetitions=1,
            model="m",
            base_generation_params={},
            prompt_template_version="v1",
            dataset_version="v1",
            execution_mode=ExecutionMode.FIXTURE,
            seed=1,
        )
    )
    assert len(observations) == 1
    sent_messages = client.calls[0].messages
    last_user_message = sent_messages[-1].content
    assert "ek metin" in last_user_message
    assert '<untrusted source="ek_belge">' in last_user_message


def test_generic_failure_recorded_as_error_not_crash():
    class _FailingClient:
        def complete(self, request):
            raise RuntimeError("boom")

    runner = ExperimentRunner(
        client=_FailingClient(), evaluator=_evaluator, pricing_lookup=lambda _m: None
    )
    conditions = [Condition("baseline", lambda: PromptComponents(instruction="x"))]
    cases = [Case("c1", "m1", {"label": "billing"})]
    observations = list(
        runner.run(
            lab_id="lab01",
            run_id="run1",
            conditions=conditions,
            cases=cases,
            repetitions=1,
            model="m",
            base_generation_params={},
            prompt_template_version="v1",
            dataset_version="v1",
            execution_mode=ExecutionMode.FIXTURE,
            seed=1,
        )
    )
    assert observations[0].error == "boom"
    assert observations[0].skip_reason is None
