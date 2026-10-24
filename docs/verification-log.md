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
