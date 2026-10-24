from __future__ import annotations

from pathlib import Path

import pytest

from lab_core.config import ConfigError, load_config


def test_default_config_loads(default_config):
    assert default_config.groq.default_model == "openai/gpt-oss-20b"
    assert default_config.execution.live_api_enabled is False


def test_minimal_valid_toml_loads(minimal_valid_toml: Path):
    config = load_config(default_path=minimal_valid_toml)
    assert config.profiles.classroom.max_cases == 10
    assert config.profiles.full.repetitions == 3


def test_unknown_top_level_key_rejected(tmp_path: Path, minimal_valid_toml: Path):
    broken = tmp_path / "broken.toml"
    broken.write_text(
        minimal_valid_toml.read_text(encoding="utf-8") + "\n[nonsense]\nx = 1\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError):
        load_config(default_path=broken)


def test_unknown_nested_key_rejected(tmp_path: Path, minimal_valid_toml: Path):
    broken = tmp_path / "broken.toml"
    text = minimal_valid_toml.read_text(encoding="utf-8").replace(
        "[execution]\nlive_api_enabled = false",
        "[execution]\nlive_api_enabled = false\ntypo_field = true",
    )
    broken.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(default_path=broken)


def test_missing_required_key_rejected(tmp_path: Path, minimal_valid_toml: Path):
    broken = tmp_path / "broken.toml"
    text = minimal_valid_toml.read_text(encoding="utf-8").replace(
        'default_model = "openai/gpt-oss-20b"\n', ""
    )
    broken.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(default_path=broken)


def test_invalid_repetitions_rejected(tmp_path: Path, minimal_valid_toml: Path):
    broken = tmp_path / "broken.toml"
    text = minimal_valid_toml.read_text(encoding="utf-8").replace(
        "repetitions = 1\n", "repetitions = 0\n"
    )
    broken.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(default_path=broken)


def test_invalid_default_profile_rejected(tmp_path: Path, minimal_valid_toml: Path):
    broken = tmp_path / "broken.toml"
    text = minimal_valid_toml.read_text(encoding="utf-8").replace(
        'default_profile = "classroom"', 'default_profile = "nonsense"'
    )
    broken.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(default_path=broken)


def test_layering_override_file_wins(tmp_path: Path, minimal_valid_toml: Path):
    override = tmp_path / "override.toml"
    override.write_text("[execution]\nlive_api_enabled = true\n", encoding="utf-8")
    config = load_config(default_path=minimal_valid_toml, override_path=override)
    assert config.execution.live_api_enabled is True
    # Untouched keys from the base file survive the merge.
    assert config.groq.default_model == "openai/gpt-oss-20b"


def test_layering_cli_overrides_win_over_file(tmp_path: Path, minimal_valid_toml: Path):
    override = tmp_path / "override.toml"
    override.write_text("[execution]\nlive_api_enabled = true\n", encoding="utf-8")
    config = load_config(
        default_path=minimal_valid_toml,
        override_path=override,
        cli_overrides={"profiles": {"classroom": {"max_cases": 5, "repetitions": 1}}},
    )
    assert config.profiles.classroom.max_cases == 5
    assert config.execution.live_api_enabled is True  # file layer still applies


def test_pricing_for_missing_model_is_none(default_config):
    assert default_config.pricing_for("some/unknown-model") is None


def test_pricing_cached_input_unverified_is_none(default_config):
    pricing = default_config.pricing_for("openai/gpt-oss-20b")
    assert pricing is not None
    assert pricing.cached_input_per_1m_usd is None
    assert pricing.input_per_1m_usd == pytest.approx(0.075)
