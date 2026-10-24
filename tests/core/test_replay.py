from __future__ import annotations

from pathlib import Path

import pytest

from lab_core.config import TokensConfig
from lab_core.evaluation import EvaluationResult, closed_set_match
from lab_core.execution_mode import ExecutionMode
from lab_core.experiment_runner import Case, Condition, ExperimentRunner
from lab_core.fake_client import FakeGroqClient
from lab_core.prompt_builder import PromptComponents
from lab_core.replay import persist_replay, run_replay
from lab_core.results_writer import ResultsWriter

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def _evaluator(content: str, case: Case) -> EvaluationResult:
    predicted = content.strip()
    correct = closed_set_match(predicted, case.expected["label"])
    return EvaluationResult(checks={"ok": True}, primary_correct=correct, parsed_label=predicted)


def _make_source_run(tmp_path: Path, instruction: str = "Siniflandir.") -> Path:
    client = FakeGroqClient(resolver=lambda _r: "billing", tokens_config=TOKENS_CFG)
    runner = ExperimentRunner(client=client, evaluator=_evaluator, pricing_lookup=lambda _m: None)
    conditions = [Condition("baseline", lambda: PromptComponents(instruction=instruction))]
    cases = [
        Case("c1", "mesaj", {"label": "billing"}),
        Case("c2", "mesaj2", {"label": "complaint"}),
    ]

    writer = ResultsWriter(tmp_path / "results")
    # Source run is labeled a synthetic test recording, not a real live call (none was made).
    handle = writer.start_run("lab01", ExecutionMode.SYNTHETIC_RECORDING_FOR_TESTS, run_metadata={})
    for obs in runner.run(
        lab_id="lab01",
        run_id=handle.run_id,
        conditions=conditions,
        cases=cases,
        repetitions=1,
        model="openai/gpt-oss-20b",
        base_generation_params={"temperature": 0.0},
        prompt_template_version="v1",
        dataset_version="v1",
        execution_mode=ExecutionMode.SYNTHETIC_RECORDING_FOR_TESTS,
        seed=1,
    ):
        handle.append_observation(obs)
    handle.write_run_metadata(
        {
            "lab_id": "lab01",
            "run_id": handle.run_id,
            "execution_mode": ExecutionMode.SYNTHETIC_RECORDING_FOR_TESTS.value,
        },
        status="completed",
    )
    return handle.directory


def test_replay_reevaluates_without_calling_a_client(tmp_path: Path):
    source_dir = _make_source_run(tmp_path)
    conditions = [Condition("baseline", lambda: PromptComponents(instruction="Siniflandir."))]
    cases = [
        Case("c1", "mesaj", {"label": "billing"}),
        Case("c2", "mesaj2", {"label": "complaint"}),
    ]

    result = run_replay(
        source_run_dir=source_dir,
        conditions=conditions,
        cases=cases,
        repetitions=1,
        prompt_template_version="v1",
        evaluator=_evaluator,
        pricing_lookup=lambda _m: None,
    )
    assert len(result.observations) == 2
    assert not result.mismatches
    assert all(o.execution_mode == "replay" for o in result.observations)
    assert all(o.source_run_id is not None for o in result.observations)
    # c1's gold is billing and the recorded response was "billing" -> correct.
    c1_obs = next(o for o in result.observations if o.case_id == "c1")
    assert c1_obs.evaluation_results["primary_correct"] is True
    # c2's gold is complaint but the recorded response was "billing" -> incorrect.
    c2_obs = next(o for o in result.observations if o.case_id == "c2")
    assert c2_obs.evaluation_results["primary_correct"] is False


def test_replay_detects_prompt_drift_and_excludes_by_default(tmp_path: Path):
    source_dir = _make_source_run(tmp_path, instruction="Siniflandir.")
    drifted_conditions = [
        Condition("baseline", lambda: PromptComponents(instruction="Farkli talimat."))
    ]
    cases = [
        Case("c1", "mesaj", {"label": "billing"}),
        Case("c2", "mesaj2", {"label": "complaint"}),
    ]

    result = run_replay(
        source_run_dir=source_dir,
        conditions=drifted_conditions,
        cases=cases,
        repetitions=1,
        prompt_template_version="v1",
        evaluator=_evaluator,
        pricing_lookup=lambda _m: None,
    )
    assert len(result.mismatches) == 2
    assert result.observations == []
    assert result.drifted is False


def test_replay_allow_prompt_drift_includes_items_and_marks_drifted(tmp_path: Path):
    source_dir = _make_source_run(tmp_path, instruction="Siniflandir.")
    drifted_conditions = [
        Condition("baseline", lambda: PromptComponents(instruction="Farkli talimat."))
    ]
    cases = [
        Case("c1", "mesaj", {"label": "billing"}),
        Case("c2", "mesaj2", {"label": "complaint"}),
    ]

    result = run_replay(
        source_run_dir=source_dir,
        conditions=drifted_conditions,
        cases=cases,
        repetitions=1,
        prompt_template_version="v1",
        evaluator=_evaluator,
        pricing_lookup=lambda _m: None,
        allow_prompt_drift=True,
    )
    assert len(result.observations) == 2
    assert result.drifted is True


def test_replay_refuses_non_live_non_synthetic_source(tmp_path: Path):
    writer = ResultsWriter(tmp_path / "results")
    handle = writer.start_run("lab01", ExecutionMode.FIXTURE, run_metadata={})
    handle.write_run_metadata(
        {"lab_id": "lab01", "run_id": handle.run_id, "execution_mode": "fixture"},
        status="completed",
    )

    with pytest.raises(ValueError):
        run_replay(
            source_run_dir=handle.directory,
            conditions=[],
            cases=[],
            repetitions=1,
            prompt_template_version="v1",
            evaluator=_evaluator,
            pricing_lookup=lambda _m: None,
        )


def test_replay_never_modifies_source_run(tmp_path: Path):
    source_dir = _make_source_run(tmp_path)
    original_contents = (source_dir / "observations.jsonl").read_text(encoding="utf-8")
    conditions = [Condition("baseline", lambda: PromptComponents(instruction="Siniflandir."))]
    cases = [
        Case("c1", "mesaj", {"label": "billing"}),
        Case("c2", "mesaj2", {"label": "complaint"}),
    ]

    result = run_replay(
        source_run_dir=source_dir,
        conditions=conditions,
        cases=cases,
        repetitions=1,
        prompt_template_version="v1",
        evaluator=_evaluator,
        pricing_lookup=lambda _m: None,
    )
    new_run_dir = persist_replay(source_dir.parents[1], "lab01", result, source_dir)

    assert new_run_dir != source_dir
    assert (source_dir / "observations.jsonl").read_text(encoding="utf-8") == original_contents
    assert (new_run_dir / "observations.jsonl").exists()
