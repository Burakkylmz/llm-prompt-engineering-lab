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
- [ ] Lab 03 (few-shot)
- [ ] Lab 04 (context selection/budget/ordering/freshness)

## M4 — Labs 05, 06, 07, 08
- [ ] Lab 05 (context rot)
- [ ] Lab 06 (lost-in-the-middle)
- [ ] Lab 07 (reasoning/decomposition)
- [ ] Lab 08 (structured outputs)

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
