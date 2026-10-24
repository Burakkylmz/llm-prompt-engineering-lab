"""TOML -> Pydantic configuration, with layering and strict unknown-key rejection.

Layering (spec Section 8): config/default.toml < selected --config file < CLI overrides.
Every nested model sets `extra="forbid"`, so a typo'd or stale key in any layer fails loudly
at load time instead of being silently ignored.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = _REPO_ROOT / "config" / "default.toml"


class ConfigError(ValueError):
    """Raised when configuration is missing required fields or has invalid values."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GroqConfig(StrictModel):
    default_model: str
    request_timeout_seconds: float = Field(gt=0)
    reasoning_effort: str | None = None
    include_reasoning: bool = False


class ExecutionConfig(StrictModel):
    live_api_enabled: bool = False
    cost_warning_message: str


class RunProfile(StrictModel):
    max_cases: int = Field(ge=1)
    repetitions: int = Field(ge=1)
    max_context_tokens: int | None = Field(default=None, ge=1)


class ProfilesConfig(StrictModel):
    classroom: RunProfile
    full: RunProfile


class ExperimentConfig(StrictModel):
    results_dir: str
    default_profile: str

    @model_validator(mode="after")
    def _validate_profile_name(self) -> ExperimentConfig:
        if self.default_profile not in ("classroom", "full"):
            raise ConfigError(
                "experiment.default_profile must be 'classroom' or 'full', "
                f"got {self.default_profile!r}"
            )
        return self


class RetryConfig(StrictModel):
    max_attempts: int = Field(ge=1)
    base_delay_seconds: float = Field(gt=0)
    max_delay_seconds: float = Field(gt=0)
    jitter: bool

    @model_validator(mode="after")
    def _validate_delay_ordering(self) -> RetryConfig:
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ConfigError("retry.max_delay_seconds must be >= retry.base_delay_seconds")
        return self


class RateLimitConfig(StrictModel):
    requests_per_minute: float = Field(gt=0)
    tokens_per_minute: float = Field(gt=0)
    max_concurrent_requests: int = Field(ge=1)


class PreflightConfig(StrictModel):
    max_requests_per_run: int = Field(ge=1)
    max_estimated_tokens_per_run: int = Field(ge=1)
    max_input_tokens_per_request: int = Field(ge=1)
    confirm_above_requests: int = Field(ge=1)


class TokensConfig(StrictModel):
    turkish_chars_per_token: float = Field(gt=0)
    default_chars_per_token: float = Field(gt=0)


class ModelPricing(StrictModel):
    input_per_1m_usd: float | None = Field(default=None, ge=0)
    output_per_1m_usd: float | None = Field(default=None, ge=0)
    cached_input_per_1m_usd: float | None = Field(default=None, ge=0)
    verified_at: str | None = None
    source_url: str | None = None
    unverified_reason: str | None = None


class PricingConfig(StrictModel):
    models: dict[str, ModelPricing] = Field(default_factory=dict)


class AppConfig(StrictModel):
    groq: GroqConfig
    execution: ExecutionConfig
    experiment: ExperimentConfig
    profiles: ProfilesConfig
    retry: RetryConfig
    rate_limit: RateLimitConfig
    preflight: PreflightConfig
    tokens: TokensConfig
    pricing: PricingConfig = Field(default_factory=PricingConfig)

    def pricing_for(self, model_id: str) -> ModelPricing | None:
        return self.pricing.models.get(model_id)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_toml(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_config(
    override_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    default_path: Path | None = None,
) -> AppConfig:
    """Load `default.toml`, layer an optional override file, then optional CLI overrides.

    `cli_overrides` is a nested dict shaped like the TOML tree, e.g.
    `{"profiles": {"classroom": {"max_cases": 10}}}`.
    """
    base_path = default_path if default_path is not None else DEFAULT_CONFIG_PATH
    raw = _load_toml(base_path)

    if override_path is not None:
        raw = _deep_merge(raw, _load_toml(override_path))

    if cli_overrides:
        raw = _deep_merge(raw, cli_overrides)

    try:
        return AppConfig.model_validate(raw)
    except ConfigError:
        raise
    except Exception as exc:  # pydantic.ValidationError, tomllib errors, etc.
        raise ConfigError(str(exc)) from exc
