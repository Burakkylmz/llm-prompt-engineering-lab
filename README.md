# LLM Prompt & Context Engineering Lab

Educational, experiment-driven Python project for a Turkish-speaking developer training
module ("Modül 3 – Prompt & Context Engineering"). Eight hypothesis-driven labs measure how
prompt and context engineering techniques affect LLM output quality, correctness,
instruction adherence, token consumption, and latency — against the Groq API
(`openai/gpt-oss-20b` by default).

See `docs/spec.md` for the full specification and `docs/project-context.md` for an overview
of the current state of the project.

## Quick start (participant)

```powershell
uv sync
uv run lab-runner list
uv run lab-runner lab01        # fixture mode (SIMULATED — pipeline test, not model evidence)
```

See `docs/participant/README.md` (Turkish) for the full guide once written, and
`docs/architecture.md` for how fixture / replay / live execution modes work.

## Development

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Live execution against the real Groq API requires `GROQ_API_KEY` in the environment **and**
`execution.live_api_enabled = true` in the selected config **and** `--live` on the command
line — see `docs/architecture.md` Section 2 and `docs/spec.md` Section 13.
