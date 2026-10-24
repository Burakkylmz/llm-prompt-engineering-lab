# Changelog

## Unreleased

### M0 — Research & architecture (2026-10-24)
- Saved `docs/spec.md` as the authoritative project specification.
- Initialized local git repository (no remote).
- Analyzed reference repositories `llm-token-economics-lab` and `llm-sampling-lab`; recorded
  adopted patterns and deviations in `docs/decisions.md`.
- Verified Groq API capabilities (models, structured outputs, reasoning, rate limits,
  pricing) directly against `console.groq.com`; recorded in `docs/groq-capabilities.md` with
  source URLs and access date.
- Added `docs/architecture.md`, `docs/experiment-methodology.md` (draft), `docs/tasks.md`,
  `docs/project-context.md`, `docs/verification-log.md`.

### M1 — Foundation (2026-10-24)
- `pyproject.toml` + `uv.lock`: groq, pydantic, jsonschema, matplotlib; dev: pytest, ruff.
- `src/lab_core/config.py`: Pydantic-validated, layered TOML config (default < override file <
  CLI overrides), rejecting unknown keys at every nesting level.
- `src/lab_core/groq_client.py`: real Groq client adapter, gated by `LiveExecutionNotAllowed`
  unless explicitly authorized; usage/timing normalization that preserves `None` for
  unreported fields; `UnsupportedCapabilityError` classification.
- `src/lab_core/fake_client.py`: resolver-driven fake client for fixture mode — no network.
- `src/lab_core/rate_limiter.py`, `tokens.py`, `metrics.py`, `execution_mode.py`.
- `src/lab_core/cli.py`: `lab-runner` entry point with `list` and the explicit-registry lab
  discovery pattern (mirrors the reference repo).
- `Dockerfile` (non-root user, two-stage `uv sync`), `compose.yaml` (bind mounts for
  config/data/results, `.env` optional), `.gitattributes` (forced LF), `.dockerignore`.
- 46 unit tests; `uv run pytest -q`, `ruff check`, `ruff format --check` all clean.
- Docker image builds; `--help`, `list`, and the full test suite verified running inside the
  container via `docker compose run`.
