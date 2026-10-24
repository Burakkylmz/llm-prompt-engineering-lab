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
