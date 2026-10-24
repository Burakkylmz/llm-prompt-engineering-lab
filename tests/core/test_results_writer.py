from __future__ import annotations

from pathlib import Path

import pytest

from lab_core.execution_mode import ExecutionMode
from lab_core.metrics import CostEstimate, PerformanceMetrics, UsageMetrics
from lab_core.results_writer import Observation, ResultsWriter


def _make_observation(case_id: str = "c1", run_id: str = "run1") -> Observation:
    return Observation(
        experiment_id="lab01:run1",
        lab_id="lab01",
        run_id=run_id,
        condition_id="baseline",
        case_id=case_id,
        repetition=1,
        execution_mode="fixture",
        timestamp="2026-10-24T00:00:00Z",
        model_id="openai/gpt-oss-20b",
        generation_parameters={"temperature": 0.0},
        prompt_template_version="v1",
        prompt_hash="abc123",
        dataset_version="v1",
        raw_response="billing",
        expected_output={"label": "billing"},
        evaluation_results={
            "checks": {"x": True},
            "primary_correct": True,
            "parsed_label": "billing",
            "notes": {},
        },
        usage=UsageMetrics(prompt_tokens=10, completion_tokens=2),
        performance=PerformanceMetrics(client_elapsed_ms=5.0),
        cost=CostEstimate(None, reason="no pricing"),
    )


def test_start_run_creates_expected_layout(tmp_path: Path):
    writer = ResultsWriter(tmp_path)
    handle = writer.start_run("lab01", ExecutionMode.FIXTURE, run_metadata={"foo": "bar"})
    assert handle.directory.exists()
    assert (handle.directory / "run.json").exists()
    assert handle.directory.parent.name == "lab01"


def test_start_run_refuses_to_overwrite(tmp_path: Path):
    writer = ResultsWriter(tmp_path)
    handle = writer.start_run("lab01", ExecutionMode.FIXTURE, run_metadata={}, run_id="fixed-id")
    with pytest.raises(FileExistsError):
        writer.start_run("lab01", ExecutionMode.FIXTURE, run_metadata={}, run_id="fixed-id")
    assert handle.directory.exists()


def test_append_observation_is_incremental(tmp_path: Path):
    writer = ResultsWriter(tmp_path)
    handle = writer.start_run("lab01", ExecutionMode.FIXTURE, run_metadata={})
    handle.append_observation(_make_observation("c1"))
    handle.append_observation(_make_observation("c2"))

    observations = handle.read_observations()
    assert len(observations) == 2
    assert {o.case_id for o in observations} == {"c1", "c2"}


def test_round_trip_preserves_none_usage_fields(tmp_path: Path):
    writer = ResultsWriter(tmp_path)
    handle = writer.start_run("lab01", ExecutionMode.FIXTURE, run_metadata={})
    obs = _make_observation()
    handle.append_observation(obs)
    loaded = handle.read_observations()[0]
    assert loaded.usage.cached_tokens is None
    assert loaded.usage.reasoning_tokens is None
    assert loaded.cost.estimated_cost_usd is None


def test_load_run_reads_metadata_written_by_start_run(tmp_path: Path):
    writer = ResultsWriter(tmp_path)
    handle = writer.start_run("lab01", ExecutionMode.FIXTURE, run_metadata={})
    handle.write_run_metadata(
        {"lab_id": "lab01", "run_id": handle.run_id, "execution_mode": "fixture"},
        status="completed",
    )

    reloaded = ResultsWriter.load_run(handle.directory)
    assert reloaded.lab_id == "lab01"
    assert reloaded.execution_mode == ExecutionMode.FIXTURE


def test_partial_run_keeps_completed_observations_on_crash(tmp_path: Path):
    writer = ResultsWriter(tmp_path)
    handle = writer.start_run("lab01", ExecutionMode.FIXTURE, run_metadata={})
    handle.append_observation(_make_observation("c1"))
    handle.write_run_metadata(
        {"lab_id": "lab01", "run_id": handle.run_id, "execution_mode": "fixture"}, status="partial"
    )

    observations = handle.read_observations()
    assert len(observations) == 1
