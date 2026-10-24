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

## M1 — Foundation
- [ ] `pyproject.toml`, `uv.lock`, `.python-version`
- [ ] `src/lab_core/`: config.py, groq_client.py, fake_client.py, rate_limiter.py, tokens.py, metrics.py, results_writer.py, cli.py
- [ ] `config/default.toml`, `config/live.example.toml`, `config/classroom.example.toml`, `.env.example`
- [ ] CLI skeleton: `list`, `--help`, lab discovery pattern
- [ ] Dockerfile, compose.yaml, .dockerignore, .gitattributes, .gitignore
- [ ] Unit tests for all of the above
- [ ] `uv run pytest -q`, `ruff check`, `ruff format --check` all passing
- [ ] Docker build + `--help` verified (or Not Verified with reason)

## M2 — Evaluation infra + Lab 01 (CHECKPOINT)
- [ ] `src/lab_core/`: prompt_builder.py, context_manager.py, experiment_runner.py, evaluation.py, statistics.py, reporting.py, replay.py
- [ ] `data/schemas/*.json` + dataset validation command
- [ ] Lab 01: dataset (eval ≥60, pool ≥15), conditions, prompts, evaluator, tests, README (TR)
- [ ] Lab 01 fixture run: local + Docker
- [ ] Synthetic recording fixture + replay test
- [ ] `docs/verification-log.md` M1+M2 entries
- [ ] Turkish checkpoint report delivered; **stop and wait**

## M3 — Labs 02, 03, 04
- [ ] Lab 02 (instruction hierarchy / injection)
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
