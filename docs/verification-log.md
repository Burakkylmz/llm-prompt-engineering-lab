# Verification Log

Append-only. Each entry records the actual command run, the environment, the exit code, and a
summary of actual output. Failures are recorded as failures.

## M0 — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `git init` | local (Windows, Git Bash) | 0 | Initialized empty repo at `C:\Users\pc\llm-prompt-engineering-lab\.git` |
| `uv --version` | local | 0 | `uv 0.11.7` present |
| `docker --version` | local | 0 | `Docker version 29.5.3` present (Docker Desktop) |
| `gh api repos/Burakkylmz/llm-token-economics-lab` | local | 0 | Repo reachable, public |
| `git clone --depth 1 https://github.com/Burakkylmz/llm-token-economics-lab.git` | scratchpad | 0 | Cloned, 50+ files read directly |
| `git clone --depth 1 https://github.com/Burakkylmz/llm-sampling-lab.git` | scratchpad | 0 | Cloned, files read directly |
| WebFetch `console.groq.com/docs/models` | network | success | Model table extracted, see `docs/groq-capabilities.md` |
| WebFetch `console.groq.com/docs/structured-outputs` | network | success | Strict/best-effort mode rules extracted |
| WebFetch `console.groq.com/docs/reasoning` | network | success | `reasoning_effort`/`include_reasoning` rules extracted |
| WebFetch `console.groq.com/docs/rate-limits` | network | success | Header names, 429 behavior extracted |
| WebFetch `console.groq.com/docs/model/openai/gpt-oss/20b` | network | success | Pricing confirmed: $0.075/1M in, $0.30/1M out |
| WebFetch `groq.com/pricing/` | network | success (no data) | Marketing page, no per-model numbers (client-rendered) |

No test suite exists yet at this milestone. M1 entry will follow once the foundation is built.

## M1 — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `uv sync` | local (Windows, Git Bash) | 0 | 38 packages installed, incl. groq, pydantic, jsonschema, matplotlib, pytest, ruff |
| `uv run pytest -q` | local | 0 | 46 passed, 0 failed |
| `uv run ruff check .` | local | 0 | All checks passed! |
| `uv run ruff format --check .` | local | 0 | 32 files already formatted |
| `uv run lab-runner --help` | local | 0 | Prints usage with `list` subcommand |
| `uv run lab-runner list` | local | 0 | `No labs registered yet.` (correct: no lab built yet) |
| Start Docker Desktop, wait for daemon | local | 0 | Daemon ready after ~2 polling cycles |
| `docker compose build` | local (Docker Desktop, Windows) | 0 | Image `llm-prompt-engineering-lab-lab-runner` built successfully |
| `docker compose run --rm lab-runner --help` | Docker | 0 | Same usage output as local run |
| `docker compose run --rm lab-runner list` | Docker | 0 | `No labs registered yet.` |
| `docker compose run --rm --entrypoint uv lab-runner run pytest -q` | Docker | 0 | 46 passed, 0 failed (same suite, inside container) |

**Not yet verified at M1 (by design — depends on M2 features that don't exist yet):**
- `docker compose run --rm lab-runner lab01` (no lab exists yet).
- "Config and dataset changes on the host take effect without rebuild" — bind mounts
  (`./config:/app/config:ro`, `./data:/app/data:ro`, `./results:/app/results`) are configured
  in `compose.yaml` and structurally correct, but no lab yet reads config/data at runtime to
  exercise this end-to-end; re-verified in the M2 entry once Lab 01 exists.
- Live Groq API call: **Not Verified — no `GROQ_API_KEY` in this environment.** The safety
  gates that would prevent one are unit-tested (`tests/core/test_safety.py`,
  `tests/core/test_groq_client.py`).

## M2 — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `uv run pytest -q` | local | 0 | 148 passed, 0 failed (final count after adding the pre-flight plan module) |
| `uv run ruff check .` | local | 0 | All checks passed! |
| `uv run ruff format --check .` | local | 0 | all files already formatted |
| `uv run lab-runner list` | local | 0 | `Available labs:\n  lab01` |
| `uv run lab-runner validate-data` | local | 0 | `lab01: OK` (schema + class-balance + edge-fraction + leakage checks) |
| `uv run lab-runner lab01 --profile classroom --max-cases 10` | local | 0 | Fixture run; 6 conditions x 10 cases x 1 rep = 60 observations; `comparison.md`/`summary.json`/chart generated; SIMULATED banner present |
| `uv run lab-runner report <run_dir>` | local | 0 | Regenerated `summary.json` after deleting it, from `observations.jsonl` alone |
| `docker compose build` | local (Docker Desktop) | 0 | Rebuilt with Lab 01 included |
| `docker compose run --rm lab-runner list` | Docker | 0 | `lab01` listed |
| `docker compose run --rm lab-runner validate-data` | Docker | 0 | `lab01: OK` |
| `docker compose run --rm lab-runner lab01 --profile classroom --max-cases 10` | Docker | 0 | Run directory appeared on the **host** `results/lab01/` via the bind mount |
| `docker compose run --rm lab-runner lab01 --replay tests/fixtures/recordings/lab01/synthetic-test-recording-001` | Docker | 0 | Replay run produced; source recording untouched |
| `docker compose run --rm --entrypoint uv lab-runner run pytest -q` | Docker | 0 | 137 passed, 0 failed (identical suite, in-container; re-verified at 148 passed after the pre-flight-plan addition below) |
| Manual check: edited `config/default.toml` on host (`profiles.classroom.max_cases`), re-ran `docker compose run --rm lab-runner lab01` **without rebuilding** | local + Docker | 0 | `run.json` showed `"n_cases": 7"` reflecting the host edit; config reverted immediately after (confirmed `git diff` clean) — bind-mount-without-rebuild requirement verified |

**Dataset:** Lab 01 eval set has 73 cases (min 60), 5 classes with 14/14/14/14/17 per class
(min 12/class), 15.1% edge/ambiguous-tagged (min 15%); example pool has 20 cases (min 15),
zero leakage against eval (shingle-Jaccard threshold 0.8).

**Replay/synthetic recording:** `tests/fixtures/recordings/lab01/synthetic-test-recording-001/`
is committed, labeled `execution_mode: "synthetic_recording_for_tests"`, and is used only by
`tests/integration/test_lab01_cli.py` and the Docker command above — never presented as
real model evidence.

**Not verified at M2 (same reason as M1):**
- Live Groq API call for Lab 01: **Not Verified — no `GROQ_API_KEY` in this environment.**
  The live code path (`--live` + `execution.live_api_enabled=true`) exists, is wired through
  Lab 01's CLI, and is safety-gated by unit tests, but no real request has been sent.

**Gap found and fixed during M2 self-review:** the spec's Section 7 pre-flight plan (print
planned requests/estimated tokens/largest request/estimated cost before any live call; abort
over configured limits; require `--yes` above a lower confirmation threshold) was missing
from the initial Lab 01 CLI. Added `src/lab_core/preflight.py` (11 new unit tests) and wired
it into Lab 01's live path before client construction; added two CLI integration tests
confirming both the abort and the confirmation-required paths. Final count after this fix:
148 unit/integration tests, re-verified locally and in Docker (`docker compose build` +
`docker compose run --rm --entrypoint uv lab-runner run pytest -q` → 148 passed).

## M3 (Lab 02) — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `uv run pytest -q` | local | 0 | 177 passed, 0 failed |
| `uv run ruff check .` / `ruff format --check .` | local | 0 | clean |
| `uv run lab-runner validate-data` | local | 0 | `lab01: OK`, `lab02: OK` |
| `uv run lab-runner lab02 --profile classroom --max-cases 10` | local | 0 | 8 conditions x 10 cases x 1 rep = 80 observations; `attack_success.png` + `accuracy_by_condition.png` generated |
| `docker compose build` | local (Docker Desktop) | 0 | Rebuilt with Lab 02 |
| `docker compose run --rm lab-runner lab02 --profile classroom --max-cases 10` | Docker | 0 | Run appeared on host `results/lab02/` |
| `docker compose run --rm --entrypoint uv lab-runner run pytest -q` | Docker | 0 | 177 passed |

**Key design-validation result (fixture/SIMULATED mode only):** condition `C_enforced` showed
`system_level_attack_success = 0%` while `model_level_attack_success = 100%` (same as
`A_naive_concat`/`B_separated`), and `A_naive_concat`'s and `B_separated`'s model-level
success were identical — exactly the pattern the hypothesis predicts. This is a pipeline
correctness check (fixture mode, deliberately-vulnerable simulated model), **not evidence
that labeling is ineffective or that enforcement works against a real model** — that claim
can only come from a `--replay` or `--live` run.

**Not verified:** live Groq call for Lab 02 — no `GROQ_API_KEY` in this environment.

## M3 (Lab 03) — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `uv run pytest -q` | local | 0 | 207 passed, 0 failed |
| `uv run ruff check .` / `ruff format --check .` | local | 0 | clean |
| `uv run lab-runner validate-data` | local | 0 | `lab01: OK`, `lab02: OK`, `lab03: OK` |
| `uv run lab-runner lab03 --profile classroom --max-cases 20` | local | 0 | 11 conditions x 20 cases x 1 rep = 220 observations; paired design confirmed (identical case set across all 11 conditions) |
| `docker compose build` | local | 0 | Rebuilt with Lab 03 |
| `docker compose run --rm lab-runner lab03 --profile classroom --max-cases 20` | Docker | 0 | Run appeared on host `results/lab03/` |
| `docker compose run --rm --entrypoint uv lab-runner run pytest -q` | Docker | 0 | 207 passed |

**Bug found and fixed while building Lab 03:** `wilson_ci` could return a `high` (or `low`)
bound a tiny float epsilon on the wrong side of the point estimate at the extremes (e.g.
successes == n), which crashed `reporting.render_accuracy_chart` with
`ValueError: 'yerr' must not contain negative values` the first time a condition hit exactly
100% accuracy (ubiquitous in fixture mode, since Lab 03's fixture resolver always returns
the gold label). Fixed in `lab_core/statistics.py` by clamping both bounds to always contain
the point estimate; added a regression test
(`test_wilson_ci_interval_always_contains_point_estimate`) and re-ran the full suite —
178 passed immediately after the fix, with no change to any other test's expected values
(Labs 01/02's charts had simply not hit this exact floating-point edge case before).

**Not verified:** live Groq call for Lab 03 — no `GROQ_API_KEY` in this environment.

## M3 (Lab 04) — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `uv run pytest -q` | local | 0 | 250 passed, 0 failed |
| `uv run ruff check .` / `ruff format --check .` | local | 0 | clean |
| `uv run lab-runner validate-data` | local | 0 | `lab01`..`lab04: OK` |
| `uv run lab-runner lab04 --profile classroom --max-cases 10` | local | 0 | 9 conditions x 10 cases x 1 rep = 90 observations; selection-level metrics table in `comparison.md`; `budget_vs_recall_accuracy.png` generated |
| `docker compose build` | local | 0 | Rebuilt with Lab 04 |
| `docker compose run --rm lab-runner lab04 --profile classroom --max-cases 10` | Docker | 0 | Run appeared on host `results/lab04/` |
| `docker compose run --rm --entrypoint uv lab-runner run pytest -q` | Docker | 0 | 250 passed |

**Bug found and fixed while building Lab 04:** `context_manager.filter_fresh`'s set logic
was inverted — it collected the *replacement* document's ID into a drop-set and filtered
based on that, which dropped the **current** document and kept the **stale** one (exactly
backwards). Caught by `tests/core/test_context_manager.py::test_filter_fresh_drops_superseded_docs`
before any Lab 04 dataset-dependent test ran. Fixed to the trivially correct form
(`[doc for doc in docs if doc.superseded_by is None]`); all context_manager tests pass.

**Design-validation result (fixture/SIMULATED mode only):** conditions with a freshness
filter (`relevance_dedup_fresh_top5`, `order_relevance_asc`, `order_seeded_random`) showed
0% stale-document inclusion, while every other condition (including
`relevance_dedup_top5`, which has deduplication but no freshness filter) showed 100% —
confirming the hypothesis that deduplication and freshness filtering catch different
problems, in this exact dataset. Evidence recall was 100% in every condition for this small
corpus; evidence precision varied widely (5–24%) because many documents share generic
Turkish policy vocabulary. This is a pipeline-correctness/dataset-design check, not
evidence about real model behavior.

**Not verified:** live Groq call for Lab 04 — no `GROQ_API_KEY` in this environment.

## M4 (Lab 06) — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `uv run pytest -q` | local | 0 | 287 passed |
| `uv run ruff check .` / `ruff format --check .` | local | 0 | clean |
| `uv run lab-runner validate-data` | local | 0 | `lab01`..`lab06: OK` |
| `uv run lab-runner lab06 --profile classroom --max-cases 10` | local | 0 | 5 position conditions x 10 cases; U-shaped curve: 100%/0%/0%/0%/100% (fixture rule) |
| `docker compose build` + `run --rm lab-runner lab06 ...` + `run --rm --entrypoint uv ... pytest -q` | Docker | 0 | Run appeared on host; 287 passed in-container |

**Not verified:** live Groq call for Lab 06 — no `GROQ_API_KEY` in this environment.

## M4 (Lab 07) — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `uv run pytest -q` | local | 0 | 320 passed |
| `uv run ruff check .` / `ruff format --check .` | local | 0 | clean |
| `uv run lab-runner validate-data` | local | 0 | `lab01`..`lab07: OK` |
| `uv run lab-runner lab07 --profile classroom --max-cases 10` | local | 0 | 7 conditions x 10 cases; `multi_call_decomposition` observations each record `api_call_count=4`; `direct_answer` each record `1` |
| `docker compose build` + `run --rm lab-runner lab07 ...` + `run --rm --entrypoint uv ... pytest -q` | Docker | 0 | Run appeared on host; 320 passed in-container |

**Bug found and fixed while building Lab 07:** running the full 70-case dataset through
`run_multi_call_decomposition` end to end (before writing any lab-specific test) revealed
every case with a non-"clean" amount producing wrong `applicable_rules`/`rule_outcomes` —
traced to `parsing.parse_facts` misreading a round-tripped Python float string (e.g.
"800.0") as Turkish thousands-separator notation, inflating amounts ~10x. Fixed by
disambiguating on the presence of a comma; re-ran the full 70-case dataset with zero
mismatches after the fix, then added a regression test.

**Not verified:** live Groq call for Lab 07 — no `GROQ_API_KEY` in this environment. Note
for whoever runs the live-smoke procedure: `multi_call_decomposition`/`multi_call_validated`
make 4–5x the API calls of the other conditions per case; size `preflight` limits
accordingly (see Lab 07's README, "Instructor Notes").

## M4 (Lab 05) — 2026-10-24

| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| `uv run pytest -q` | local | 0 | 273 passed |
| `uv run ruff check .` / `ruff format --check .` | local | 0 | clean |
| `uv run lab-runner validate-data` | local | 0 | `lab01`..`lab05: OK` |
| `uv run lab-runner lab05 --profile classroom --max-cases 10` | local | 0 | 5 length conditions x 10 cases; `accuracy_vs_length.png` generated; degradation curve 100%→100%→0%→0%→0% (fixture rule) |
| `docker compose build` + `run --rm lab-runner lab05 ...` + `run --rm --entrypoint uv ... pytest -q` | Docker | 0 | Run appeared on host; 273 passed in-container |

**Not verified:** live Groq call for Lab 05 — no `GROQ_API_KEY` in this environment. Note
for whoever runs the live-smoke procedure: Lab 05's 32K-token condition is the single
largest request of any lab so far; check it against the account's actual context-window and
`preflight.max_input_tokens_per_request` before running live (see Lab 05's README,
"Instructor" section).
