# Project Context

`llm-prompt-engineering-lab` is an experiment-driven training project for a Turkish-speaking
developer training module ("Modül 3 – Prompt & Context Engineering"). It is built per
`docs/spec.md` (the authoritative specification — read that file first for anything not
covered here).

**What this is:** eight independent, hypothesis-driven labs sharing one core infrastructure
(`src/lab_core/`), each measuring how a specific prompt/context-engineering technique affects
a Turkish-enterprise LLM task, using Groq's `openai/gpt-oss-20b` by default. Every lab can run
against a deterministic fake client (`fixture`, the default — pipeline test only, not evidence
of model behavior), against a previously recorded live run (`replay` — the main classroom
mode), or against the real Groq API (`live`).

**What this is not:** an API demo collection, a LangChain/agent-framework showcase, or a
production service. There is no vector DB, no web frontend, no database server.

**Current status:** see `docs/tasks.md` for live milestone status and `docs/verification-log.md`
for what has actually been run and verified versus not-yet-verified in this environment (most
notably: no `GROQ_API_KEY` is available here, so no live Groq call has been made; live paths
are implemented and gated/tested but not exercised).

**Where to look:**
- `docs/architecture.md` — how the shared core is structured and why.
- `docs/experiment-methodology.md` — per-lab hypothesis, variables, dataset, threats to validity.
- `docs/decisions.md` — what was adopted from the reference repos, what changed, why.
- `docs/groq-capabilities.md` — verified Groq API facts with source URLs and access dates.
- `docs/statistics.md` — how confidence intervals/bootstrap/flips are computed and why small
  classroom runs are noisy (written in M2 alongside the Statistics module).
