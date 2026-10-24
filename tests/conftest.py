from __future__ import annotations

from pathlib import Path

import pytest

from lab_core.config import AppConfig, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def default_config() -> AppConfig:
    return load_config()


@pytest.fixture
def minimal_valid_toml(tmp_path: Path) -> Path:
    """A complete, schema-valid config written fresh per test (so tests can mutate a copy
    of the raw dict without depending on the shipped config/default.toml staying in sync)."""
    content = """
[groq]
default_model = "openai/gpt-oss-20b"
request_timeout_seconds = 30.0
reasoning_effort = "low"
include_reasoning = false

[execution]
live_api_enabled = false
cost_warning_message = "warning"

[experiment]
results_dir = "results"
default_profile = "classroom"

[profiles.classroom]
max_cases = 10
repetitions = 1
max_context_tokens = 8000

[profiles.full]
max_cases = 1000
repetitions = 3

[retry]
max_attempts = 3
base_delay_seconds = 1.0
max_delay_seconds = 10.0
jitter = true

[rate_limit]
requests_per_minute = 20.0
tokens_per_minute = 6000.0
max_concurrent_requests = 1

[preflight]
max_requests_per_run = 100
max_estimated_tokens_per_run = 200000
max_input_tokens_per_request = 50000
confirm_above_requests = 50

[tokens]
turkish_chars_per_token = 3.3
default_chars_per_token = 4.0

[pricing.models."openai/gpt-oss-20b"]
input_per_1m_usd = 0.075
output_per_1m_usd = 0.30
verified_at = "2026-10-24"
source_url = "https://console.groq.com/docs/model/openai/gpt-oss/20b"
"""
    path = tmp_path / "test_config.toml"
    path.write_text(content, encoding="utf-8")
    return path
