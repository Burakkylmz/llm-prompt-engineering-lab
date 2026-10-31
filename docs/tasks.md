# Task Tracker

Status values: `todo`, `in_progress`, `done`, `blocked`, `not_applicable`.

## M0 — Research & architecture
- [x] Save `docs/spec.md`
- [x] `git init`, local repo only
- [x] Clone & read both reference repos (scratchpad, not committed)
- [x] Fetch & record Groq docs (models, structured-outputs, reasoning, rate-limits, pricing) → `docs/groq-capabilities.md`
- [x] `docs/decisions.md`
- [x] `docs/architecture.md`
- [x] `docs/experiment-methodology.md` (draft; Lab 01 section final)
- [x] `docs/tasks.md` (this file)

## M1 — Foundation (done 2026-10-24)
- [x] `pyproject.toml`, `uv.lock`, `.python-version`
- [x] `src/lab_core/`: config.py, groq_client.py, fake_client.py, rate_limiter.py, tokens.py, metrics.py, cli.py, execution_mode.py
  (results_writer.py deferred to M2, alongside experiment_runner.py which defines the Observation shape it writes)
- [x] `config/default.toml`, `config/live.example.toml`, `config/classroom.example.toml`, `.env.example`
- [x] CLI skeleton: `list`, `--help`, lab discovery pattern (hardcoded `LAB_MODULES`, empty until M2)
- [x] Dockerfile, compose.yaml, .dockerignore, .gitattributes, .gitignore
- [x] Unit tests for all of the above (46 tests)
- [x] `uv run pytest -q` (46 passed), `ruff check` (clean), `ruff format --check` (clean)
- [x] Docker build + `--help` + `list` + in-container pytest all verified (see verification-log.md)

## M2 — Evaluation infra + Lab 01 (CHECKPOINT) — done 2026-10-24
- [x] `src/lab_core/`: prompt_builder.py, experiment_runner.py, evaluation.py, statistics.py,
  reporting.py, replay.py, results_writer.py, datasets.py, text_similarity.py, preflight.py
  (`context_manager.py` deliberately deferred to M3 — Lab 01 does no retrieval/selection;
  see `docs/decisions.md`)
- [x] `data/schemas/lab01_case_set.schema.json` + `lab-runner validate-data` command
- [x] Lab 01: dataset (eval 73 ≥60, pool 20 ≥15, 15.1% edge/ambiguous ≥15%), 6 conditions
  (baseline/A/B/B_len/C/D), evaluator, tests (dataset/conditions/evaluator/integration),
  README (TR)
- [x] Lab 01 fixture run: local + Docker (verified)
- [x] Synthetic recording fixture (`tests/fixtures/recordings/lab01/`) + replay test (incl.
  prompt-drift detection), local + Docker
- [x] `docs/verification-log.md` M1+M2 entries
- [x] `docs/statistics.md`, `docs/live-smoke.md` written
- [x] Pre-flight plan for live runs (spec Section 7) — found missing during self-review,
  implemented (`lab_core/preflight.py`) and wired into Lab 01 before the checkpoint
- [x] Turkish checkpoint report delivered; **stopped, awaiting user review**

## M3 — Labs 02, 03, 04
- [x] Lab 02 (instruction hierarchy / injection) — done 2026-10-24: 8 condition_ids (incl.
  injection/benign split per family), 65-case dataset (30 clean/25 injection across 5 types/10
  benign), two extra evaluator variants (`evaluate_response_enforced`,
  `evaluate_response_direct_conflict`), dedicated attack-success chart, synthetic recording +
  replay test, 177 tests passing, verified in Docker. Required a core extension
  (`Condition.build_user_input`) to support per-case untrusted content — added
  backward-compatibly, Lab 01 untouched/still passing.
- [x] Lab 03 (few-shot) — done 2026-10-24: 11 conditions (count series 0/2/4/8, quality
  series at k=4: random x3 seeds, redundant, diverse-typical, boundary-focused, misleading),
  93-case/5-class dataset (23.7% edge) + 31-case tagged pool, true paired design (shared
  case set), quality-vs-tokens chart, synthetic recording + replay, 207 tests passing,
  verified in Docker. Found and fixed a real `wilson_ci` floating-point bug along the way
  (interval could fall a hair outside the point estimate at 100%/0% accuracy, breaking the
  accuracy chart's error bars) — fixed at the source with a regression test.
- [x] Lab 04 (context selection/budget/ordering/freshness) — done 2026-10-24: built
  `context_manager.py` (deferred from M2 — see decisions.md); 9 conditions
  (all_documents/relevance_top5/+dedup/+dedup+fresh/3-point budget series/2 orderings);
  42-doc corpus (10 current/superseded pairs, 4 exact dup, 6 near-dup, 12 irrelevant) + 30
  questions; selection-level metrics (no LLM) computed directly; budget-vs-recall-accuracy
  chart; synthetic recording + replay; 250 tests passing, verified in Docker. Found and
  fixed a real logic-inversion bug in `filter_fresh` (kept the superseded doc, dropped the
  current one) via a unit test before it reached the dataset-dependent tests.

## M4 — Labs 05, 06, 07, 08
- [x] Lab 05 (context rot) — done 2026-10-24: added `assemble_fixed_length` to
  context_manager.py (shared with Lab 06); 5 length conditions (1K/4K/8K/16K/32K tokens,
  fixed 50% position, fixed 10% near-miss density); 20-fact dataset + 2,300-sentence filler
  pool (covers 32K tokens with zero repetition); length-exceeds-limit skip logic (tested);
  accuracy-vs-length chart; synthetic recording + replay; 273 tests passing, verified in
  Docker. Fixture mode shows the intended 3-stage degradation pattern (correct -> confused
  by near-miss -> not-found) via a deliberately simple deterministic rule.
- [x] Lab 06 (lost-in-the-middle) — done 2026-10-24: reuses Lab 05's fact/filler pool
  (spec-permitted); 5 position conditions (0/25/50/75/100%) at a fixed ~8000-token length;
  evidence-identification metric (clause ID citation); accuracy-by-position chart;
  synthetic recording + replay; 287 tests passing, verified in Docker. Fixture mode shows
  the classic U-shaped curve via a deliberately simple character-offset-ratio rule.
- [x] Lab 07 (reasoning/decomposition) — done 2026-10-24: 7 conditions (4 primary:
  direct/single-call-structured/multi-call/multi-call+validated + 3-way reasoning_effort
  sweep on direct-answer only); 70-case expense-eligibility dataset with gold intermediate
  values; custom multi-call orchestration bypassing ExperimentRunner (documented); a
  deterministic bounded-re-ask validator (tested directly with a crafted fake client, since
  the always-correct fixture never triggers it); Lab-07-specific lightweight replay (no
  prompt-hash drift detection — documented scope reduction); accuracy-vs-cost chart; 320
  tests passing, verified in Docker. Found and fixed a real number-parsing bug
  (Turkish-vs-plain decimal notation ambiguity corrupting round-tripped amounts).
- [x] Lab 08 (structured outputs) — done 2026-10-24 (partial verification, see below):
  5 conditions (plain_nl/prompt_only_json/json_object_mode/json_schema_best_effort/
  json_schema_strict); 45-record dataset (missing fields, multiple-candidate values,
  normalization-required amounts); 3-layer evaluator (JSON parse / schema adherence via
  `jsonschema` / semantic accuracy); three-layer chart; 339 tests passing locally.
  **Not done at this checkpoint:** Docker verification and the synthetic-recording/replay
  test were skipped (session usage-limit cutoff during M4) — this lab uses the standard
  `ExperimentRunner`/`run_replay` path already covered by generic tests in M2, so risk is
  low, but it has no lab-specific replay verification yet. Flagged honestly rather than
  marked done. **Resolved 2026-10-31** — see "Topic-coverage completion" below (Docker
  verification of Lab 08 is still open; see verification-log.md).

## Topic-coverage completion (2026-10-31)
Review of the eight module topics against spec Sections 10–12; details and rationale in
`docs/decisions.md` (2026-10-31 entry).
- [x] Fix: replay ignored `Condition.build_user_input` (Labs 02/04/05/06 dropped recorded
  items as drift) + cross-lab "replays completely" test
- [x] Fix: per-check rate denominators (Lab 03 edge-case accuracy diluted; Lab 07
  intermediate checks) + Lab 07 `intermediates_expected`
- [x] Fix: Lab 07 usage totals no longer partial-sum unreported fields
- [x] Fix: Lab 01 `format_compliant` accepted trailing text
- [x] Fix: `lab-runner report` crashed for Labs 05/06 and dropped lab-specific charts
  everywhere → per-lab `regenerate_report` hook + all-labs test
- [x] Reporting (spec Section 10): bootstrap CI for macro-F1 and paired differences,
  exploratory McNemar, per-check table, tokens/cost per correct, reasoning tokens, per-class
  P/R + confusion matrices, repetition consistency
- [x] Lab 01: length-bound + "all constraints met" checks, instruction-adherence chart,
  leave-one-out ablation (`--ablation` / `--profile full`)
- [x] Lab 03: example-order series (`--order-effect` / `--profile full`)
- [x] Lab 04: estimated context tokens + budget utilization
- [x] Lab 08: synthetic recording + three-layer replay test
- [ ] Docker re-verification of all of the above — **Not Verified** in this session (no
  Docker available in the environment used; see verification-log.md)

## M5 — Integration
- [ ] Full offline suite across all labs
- [ ] `scripts/smoke.ps1` / `scripts/smoke.sh` for all 8 labs
- [ ] `docs/live-smoke.md` + procedure

## M6 — Documentation & final report
- [ ] Participant/instructor guides (TR), all per-lab READMEs (TR)
- [ ] Dead-code cleanup, command verification pass
- [ ] Definition of Done review (Section 18)
- [ ] Final delivery report (TR)

---
**Known constraints for this execution environment (recorded, not hidden):**
- No `GROQ_API_KEY` available → no live Groq calls possible. All "live" paths are implemented
  and unit-tested against the safety gates, but never actually exercised; live verification is
  marked **Not Verified: no API key in this environment** throughout.
- Docker Desktop is present and will be used for Docker verification.
