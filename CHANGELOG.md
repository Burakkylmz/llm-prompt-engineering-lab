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

### M3 — Lab 03: Few-Shot Example Engineering (2026-10-24)
- Lab 03: 11 conditions across two series (count: 0/2/4/8 at a fixed selection strategy;
  quality: k=4 fixed, varying strategy — random x3 seeds, redundant, diverse-typical,
  boundary-focused, misleading), a true paired design (all 11 conditions share one eval case
  set), a 93-case/5-class dataset (23.7% edge-tagged) with a 31-case example pool tagged by
  selection purpose, a quality-vs-tokens chart, a synthetic recording fixture + replay test,
  Turkish README.
- **Fixed a real bug** in `lab_core.statistics.wilson_ci`: at the 100%/0%-accuracy extremes,
  floating-point rounding could put a CI bound a hair outside the point estimate, crashing
  the accuracy chart's error-bar computation. Fixed at the source with a regression test;
  re-verified the full suite (including Labs 01/02) afterward.
- 207 tests total; verified locally and in Docker.

### M3 — Lab 04: Context Selection, Budget, Ordering & Freshness (2026-10-24)
- Built `src/lab_core/context_manager.py` (deferred from M2): BM25 relevance scoring with
  Turkish-aware normalization, exact+near-duplicate deduplication, freshness filtering,
  4 ordering strategies, greedy token-budget selection.
- Lab 04: 9 conditions (all_documents baseline, relevance-only, +dedup, +dedup+freshness, a
  3-point budget series, 2 additional orderings of the fixed set), a 42-document corpus (10
  current/superseded topic pairs, 4 exact duplicates, 6 near-duplicates, 12 irrelevant
  documents) and 30 questions with gold answers/evidence/stale values. Selection-level
  metrics (evidence recall/precision, stale-document inclusion rate) computed directly from
  each selector — no LLM call, always real even in fixture mode. Budget-vs-recall-accuracy
  chart, synthetic recording + replay test, Turkish README.
- **Fixed a real bug** in `context_manager.filter_fresh`: the set-membership logic was
  inverted, dropping the current document and keeping the superseded one. Caught by a unit
  test before any Lab 04 dataset-dependent test ran.
- 250 tests total; verified locally and in Docker. Fixture-mode run confirms the intended
  finding: deduplication alone does not remove stale documents (0% vs. 100% stale-inclusion
  only once freshness filtering is added) — a dataset/pipeline-design validation, not
  evidence about real model behavior.

### M4 — Lab 05: Context Rot (2026-10-24)
- Added `context_manager.assemble_fixed_length` (shared with Lab 06): builds coherent
  filler text to an approximate token target with a target sentence inserted at a given
  relative position and near-miss distractors mixed in at a given density.
- Lab 05: 5 length conditions (1000/4000/8000/16000/32000 estimated tokens) at a fixed 50%
  position and 10% near-miss density; 20 target facts (4 types x 5 values) each with a
  near-miss counterpart; a 2,300-sentence combinatorially-generated filler pool covering the
  longest length without repeating any sentence; lengths exceeding
  `preflight.max_input_tokens_per_request` are excluded from the run and recorded as skipped
  observations rather than failures (tested). Accuracy-vs-length chart, synthetic recording
  + replay test, Turkish README.
- 273 tests total; verified locally and in Docker.
