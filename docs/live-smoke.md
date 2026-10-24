# Live Smoke Procedure

Sends one minimal real request per lab against the Groq API, using the `classroom` profile,
to confirm the live path actually works before a training session. **Run this only if you
have a working `GROQ_API_KEY`.** It costs real (tiny) money. This project's own agent build
environment did not have a key, so this procedure has not been executed — every live-mode
claim elsewhere in `docs/verification-log.md` is marked **Not Verified** for that reason, not
because the code path is untested (it is, via the safety-gate unit tests).

## Prerequisites

1. `config/live.toml` exists (copy from `config/live.example.toml`) and sets
   `execution.live_api_enabled = true`.
2. `GROQ_API_KEY` is set in the environment, or in a `.env` file at the repo root
   (`cp .env.example .env` and fill it in).
3. You have reviewed `config/live.toml`'s `rate_limit` and `preflight` sections for the
   account/tier you're using — see `docs/groq-capabilities.md` Section 4.

## Procedure (PowerShell)

For each completed lab (currently only `lab01`; repeat the pattern as Labs 02–08 land):

```powershell
uv run lab-runner lab01 --live --config config/live.toml --profile classroom --max-cases 1 --repetitions 1 --yes
```

`--max-cases 1 --repetitions 1` keeps this to the smallest possible real call per condition
(6 conditions x 1 case x 1 repetition = 6 requests for Lab 01). Confirm:

1. The pre-flight plan prints and does not abort against `preflight.*` limits.
2. The `[COST WARNING]` line is printed before any request is sent.
3. The run completes and `results/lab01/<timestamp>_live_<id>/` is created with a non-empty
   `observations.jsonl`, each entry's `usage.prompt_tokens`/`completion_tokens` populated by
   the **provider** (not estimated — check these are present and plausible for the model).
4. `comparison.md` does **not** carry the SIMULATED banner (mode is `live`).

## Recording for classroom replay

Once a live smoke run looks correct, re-run with the full `classroom` profile (no
`--max-cases`/`--repetitions` override) to produce the actual replay source, then copy the
resulting run directory into `data/recordings/<lab_id>/` and commit it:

```powershell
uv run lab-runner lab01 --live --config config/live.toml --yes
Copy-Item -Recurse "results\lab01\<new_run_id>" "data\recordings\lab01\<new_run_id>"
git add data/recordings/lab01/<new_run_id>
git commit -m "Add lab01 classroom replay recording (live, <date>)"
```

Participants then use `--replay data/recordings/lab01/<new_run_id>` as their default path —
see `docs/architecture.md` Section 10 for why replay, not a shared live key, is the
recommended classroom default.

## Recording the outcome

Whoever runs this procedure appends the actual result (pass/fail, request count, any
unexpected `unsupported`/error entries) to `docs/verification-log.md` under a new dated
entry. Never mark a live run as "Passed" without having actually executed this procedure.
