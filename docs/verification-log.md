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
