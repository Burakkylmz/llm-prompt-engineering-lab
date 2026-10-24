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

### M2 — Evaluation infrastructure + Lab 01 (2026-10-24, checkpoint)
- `src/lab_core/`: `prompt_builder.py` (untrusted content never reaches the system message,
  by construction), `evaluation.py` (Turkish-aware normalization, classification metrics),
  `statistics.py` (Wilson CI, seeded bootstrap CI, paired flips, exploratory McNemar),
  `experiment_runner.py` (paired, seeded-counterbalanced execution), `results_writer.py`
  (append-only `Observation` persistence, never overwrites a run), `reporting.py`
  (`summary.json`/`comparison.md`/charts, SIMULATED watermarking), `replay.py` (prompt-hash
  matching, drift detection, never mutates the source run), `datasets.py` (schema validation,
  class-balance/edge-fraction/leakage checks, stratified subsetting), `text_similarity.py`
  (shared shingle-Jaccard similarity), `preflight.py` (pre-flight plan + abort/confirm gates
  for live runs).
- `data/schemas/lab01_case_set.schema.json`; `lab-runner validate-data` and
  `lab-runner report <run_dir>` commands.
- **Lab 01 (Prompt Anatomy & Instruction Clarity)**: 6 cumulative conditions
  (baseline/A_context/B_constraints/B_len/C_output_contract/D_examples), synthetic Turkish
  dataset (73 eval cases / 5 classes / 15.1% edge-case-tagged, 20-case example pool, zero
  leakage), deterministic evaluator (label/priority/format-compliance checks applied
  uniformly across conditions), fixture + replay paths, Turkish README.
- Committed synthetic recording fixture (`tests/fixtures/recordings/lab01/`) for testing
  replay without a live call.
- 148 unit/integration tests; `ruff check`/`format` clean; verified locally and in Docker,
  including that a host-side `config/default.toml` edit takes effect without an image rebuild.

### M3 — Lab 02: Instruction Hierarchy & Untrusted Content (2026-10-24)
- Core extension: `Condition.build_user_input` (optional, defaults to the Lab 01 behavior)
  lets a condition supply per-case untrusted content/overrides instead of a static prompt —
  backward-compatible, Lab 01 unaffected.
- Lab 02: 8 condition_ids (baseline/A/A_benign/B/B_benign/C/C_benign/D), a 65-case synthetic
  dataset (30 clean decision cases, 25 injection cases across 5 injection types, 10 benign
  controls), a deterministic refund policy + bright-line enforcement + canary-redaction
  layer, three evaluator variants (plain / enforced / direct-conflict), a dedicated
  model-vs-system-level attack-success chart, a synthetic recording fixture + replay test,
  Turkish README.
- 177 tests total; verified locally and in Docker. Fixture-mode run confirms the intended
  measurement pattern (model-level attack success stays high across A/B/C while
  system-level drops to 0% only under C's enforcement) — a pipeline-correctness result, not
  evidence about real model behavior.
