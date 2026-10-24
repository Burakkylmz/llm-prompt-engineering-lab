# MASTER SPEC — LLM Prompt Engineering & Context Engineering Lab

> **For Claude Code.** This document is both the task prompt and the project specification.
> In your first action, save it verbatim to `docs/spec.md` in the new repository. In later sessions, `docs/spec.md` is the source of truth.

---

## 0. How to Work With This Spec (read first)

You are building a large project. The main failure mode for projects of this size is a careful start, shallow later labs, trivial datasets, and self-certified completion. This spec is structured to prevent that.

**Execution protocol:**

1. Work in the milestones defined in Section 3, in order.
2. At the end of every milestone:
   - Run the relevant checks (tests, lint, Docker commands where applicable).
   - Append the evidence to `docs/verification-log.md` (format in Section 3.2).
   - Update `docs/tasks.md` statuses and `CHANGELOG.md`.
   - Create a **local** git commit (`git init` in M0). **Never push** to any remote.
3. **Mandatory checkpoint after Milestone M2** (foundation + evaluation infrastructure + Lab 01 as the reference implementation). Stop, deliver the checkpoint report (Section 3.3, in Turkish) and wait for the user to review. Continue past this checkpoint only if the user says so.
4. Between checkpoints, do not ask for approval on ordinary architecture or implementation decisions. Use engineering judgment and record significant decisions in `docs/decisions.md`.
5. Do not deliver placeholder implementations (`TODO`, `pass`, `NotImplementedError`, stub datasets) for any required feature. If something cannot be completed, say so explicitly in `docs/tasks.md` and in your report.

**Honesty rules (apply everywhere):**

- Never fabricate LLM outputs, measurements, test results, API verification, or documentation claims.
- Never present fixture or simulated results as evidence of model behavior.
- If you could not run something (no Groq key, no Docker, no network), mark it **Not Verified**, not Passed.
- If you could not access a reference repository or documentation page, record that and do not write as if you had read it.

---

## 1. Role & Mission

Act as a **Senior AI Engineer, LLM Evaluation Engineer, Software Architect, Python Developer, and Technical Training Lab Designer**.

**Project name:** `llm-prompt-engineering-lab`

**Purpose:** An educational, experiment-driven Python project for a Turkish-speaking developer training module ("Modül 3 – Prompt & Context Engineering"). It measures, through controlled experiments, how prompt and context engineering techniques affect LLM output quality, correctness, reliability, instruction adherence, token consumption, and latency.

The module topics that the project **must** cover, with their lab mapping:

| Module topic | Lab |
|---|---|
| Prompt anatomy: instruction + context + constraints + examples + output contract | Lab 01 |
| Instruction hierarchy; system/task instructions vs. untrusted content | Lab 02 |
| Few-shot examples and ambiguity-reducing example selection | Lab 03 |
| Context selection, budget, relevance, redundancy, ordering, freshness | Lab 04 |
| Context rot | Lab 05 |
| Lost-in-the-middle | Lab 06 |
| Reasoning guidance & task decomposition (instead of classic chain-of-thought) | Lab 07 |
| Structured outputs and JSON Schema; "return JSON" vs. schema adherence | Lab 08 |

Every lab follows this cycle: hypothesis → experimental design → baseline → controlled conditions → execution → measurement and evaluation → persistence → comparative analysis (with uncertainty) → technical interpretation.

This is an **experiment and teaching platform**, not an API demo collection.

---

## 2. Reference Repositories (mandatory analysis in M0)

Inspect, but do not modify:

1. https://github.com/Burakkylmz/llm-token-economics-lab
2. https://github.com/Burakkylmz/llm-sampling-lab

Analyze: project structure, shared core, lab independence, CLI and command registration, Groq integration, TOML config and validation, experiment execution, token and latency measurement, mock clients and offline tests, JSON persistence, Dockerfile / Compose, participant docs, and hypothesis-based design.

Reuse good design decisions; do not copy code wholesale. Use the shared-core architecture, modular labs, safety defaults and metrics approach of `llm-token-economics-lab` as the primary reference. The architectural novelty of this project is the **Prompt Quality Evaluation Engine** and the **replay mode** (Section 5).

Write a short summary of what you adopted, what you changed and why in `docs/decisions.md`. If a repository is inaccessible, record that and continue.

---

## 3. Milestones

### 3.1 Milestone list

| ID | Scope | Exit criteria |
|---|---|---|
| **M0** | Research & architecture: reference repos, official Groq docs, `docs/decisions.md`, `docs/architecture.md`, `docs/experiment-methodology.md` (draft), `docs/tasks.md`, `docs/groq-capabilities.md` | Docs exist; Groq capability notes cite URLs and an access date; repo initialized |
| **M1** | Foundation: packaging (uv, pyproject, lock), Dockerfile, compose.yaml, config system, Groq client adapter, fake client, CLI skeleton with `list`, execution modes, rate limiter, unit tests | `uv run pytest -q` passes; `ruff check` and `ruff format --check` pass; Docker build and `--help` verified (or marked Not Verified with reason) |
| **M2** | Evaluation infrastructure (dataset loading and validation, evaluators, statistics, results writer, comparison report, charts) **plus Lab 01 complete end-to-end** as the reference lab, including dataset, docs and tests | Lab 01 runs in fixture mode locally and in Docker; replay mode tested with a labeled synthetic recording fixture; **CHECKPOINT — stop and report** |
| **M3** | Labs 02, 03, 04 | Each lab meets its per-lab completion criteria (Section 11.0) |
| **M4** | Labs 05, 06, 07, 08 | Same |
| **M5** | Integration: full offline suite, Docker smoke scripts for all labs, host-side result persistence, live smoke procedure (run only if credentials exist) | Evidence in verification log |
| **M6** | Documentation completion, dead-code cleanup, command verification, final report | Definition of Done (Section 18) reviewed item by item |

### 3.2 Verification log format

`docs/verification-log.md`, append-only:

```markdown
## M1 — 2026-xx-xx
| Command | Environment | Exit code | Result summary |
|---|---|---|---|
| uv run pytest -q | local | 0 | 142 passed |
| docker compose build | — | — | Not Verified: Docker not available in this environment |
```

Record the actual command and the actual outcome. Summarize long output; do not paraphrase failures as successes.

### 3.3 Checkpoint report (after M2, in Turkish)

1. What was built (files, components).
2. Architecture decisions that deviate from this spec, with reasons.
3. Lab 01 design: conditions, dataset size and class balance, example fixture-mode output.
4. Verification log excerpt.
5. Open questions or risks for Labs 02–08.
6. Anything the user should decide before you continue.

---

## 4. Technology Stack

| Component | Requirement |
|---|---|
| Language | Python 3.12 |
| Package management | uv (`pyproject.toml`, committed `uv.lock`) |
| App configuration | TOML |
| LLM provider | Groq API (OpenAI-compatible chat completions) |
| Preferred model | `openai/gpt-oss-20b`, configurable, never hardcoded in lab logic |
| Validation | Pydantic (config, records), `jsonschema` (structured outputs, dataset schemas) |
| Testing | pytest |
| Lint / format | ruff (`ruff check`, `ruff format --check`) |
| Visualization | Matplotlib (headless `Agg` backend) |
| CLI | argparse or Typer |
| Containers | Docker + Docker Compose |
| Data | JSON datasets; JSON / JSONL results |

Out of scope: LangChain or other agent frameworks, vector databases, embeddings, web frontends, database servers, distributed infrastructure. Add other dependencies only with clear value and record them in `docs/decisions.md`.

**Verify before implementing** (M0), and record findings with URLs and access date in `docs/groq-capabilities.md`:

- https://console.groq.com/docs/models — model availability, context window, max output
- https://console.groq.com/docs/structured-outputs — JSON Object Mode, JSON Schema, strict mode, supported models, schema feature limitations
- https://console.groq.com/docs/reasoning — `reasoning_effort` values, how reasoning output is returned or hidden for gpt-oss models, reasoning token reporting
- https://console.groq.com/docs/rate-limits — RPM/TPM/RPD/TPD for relevant tiers, rate-limit headers, 429 behavior
- Pricing page, if accessible

Do not hardcode model availability, context windows, parameter support, or prices. Put them in config with a `verified_at` date and source URL. If something could not be verified, record it as unverified and make the code handle "unsupported" gracefully.

---

## 5. Execution Modes (core design)

There are three modes. Every result records its mode, and every report shows the mode prominently.

| Mode | How it is invoked | What it does | Evidential value |
|---|---|---|---|
| **fixture** (default) | `lab01` | Runs the full pipeline (prompt construction, context construction, client call, evaluation, statistics, persistence, report, charts) against a deterministic fake client whose responses come from labeled fixture files or deterministic rules | Tests the pipeline only. **Not evidence of model behavior.** Reports carry a banner: `SIMULATED — fixture responses, not model output` |
| **replay** | `lab01 --replay results/lab01/<live_run_id>` | Re-runs evaluation, statistics, reports and charts on raw model responses recorded in a previous **live** run. No API calls | Real model behavior, recorded at a known date with a known model ID. Main classroom mode |
| **live** | `lab01 --live --config config/live.toml` | Calls Groq. Raw responses are persisted so the run can later be replayed | Real model behavior |

**Replay rules:**

- Match recorded responses by `(lab_id, condition_id, case_id, repetition, prompt_hash)`. If the prompt hash differs (prompt template changed), report the mismatch and do not silently substitute. Allow an explicit `--allow-prompt-drift` flag that re-evaluates anyway, labels the run as drifted, and lists affected items.
- Replay must produce a new run directory; it never modifies the source live run.
- Replay lets participants change evaluators or analysis and re-run without cost. Document this as a teaching use.

**Shipping recordings:** You (the implementing agent) probably do not have a Groq key. Do **not** create fake "live" recordings. Ship:

- a small, clearly labeled synthetic recording under `tests/fixtures/recordings/` used only for testing replay (`execution_mode: "synthetic_recording_for_tests"`);
- an empty `data/recordings/` directory with a README describing the instructor procedure: run each lab live with the classroom profile before the training and commit the resulting runs as replay sources.

---

## 6. Docker Requirements

Docker Compose is the primary participant environment. Participants must be able to run all labs without installing Python, uv or dependencies.

Requirements:

- `Dockerfile` installs uv, uses `uv sync --frozen` from `uv.lock`, and runs as a non-root user.
- Multi-stage build is acceptable if it stays readable.
- `compose.yaml` with a `lab-runner` service:
  - bind mounts: `./config:/app/config:ro`, `./data:/app/data:ro`, `./results:/app/results` (read-write);
  - credentials from environment variables (`GROQ_API_KEY`), optionally loaded from `.env` via `env_file` marked as not required, so a missing `.env` does not break offline runs;
  - sensible CPU/memory limits.
- Config and dataset changes on the host take effect without rebuilding the image.
- Never embed secrets in the image. `.dockerignore` excludes `.env`, `results/`, `.venv`, caches.
- Windows Docker Desktop compatibility: add `.gitattributes` forcing LF for `*.sh`, `Dockerfile` and other files executed in the container; avoid host-path assumptions; document file-permission behavior of the results bind mount.

These commands must work (PowerShell):

```powershell
docker compose build
docker compose run --rm lab-runner --help
docker compose run --rm lab-runner list
docker compose run --rm lab-runner lab01          # fixture mode, likewise lab02..lab08
docker compose run --rm lab-runner lab01 --replay results/lab01/<run_id>
docker compose run --rm lab-runner lab01 --live --config config/live.toml
docker compose run --rm --entrypoint uv lab-runner run pytest -q
```

Docker smoke tests are **scripts**, not pytest tests (no Docker-in-Docker): `scripts/smoke.ps1` and `scripts/smoke.sh`. They build the image, run `--help` and `list`, run every lab in fixture mode, check that result files appear on the host, and run pytest inside the container. Exit non-zero on any failure.

---

## 7. Classroom, Rate-Limit and Cost Constraints

The training runs with a group of developers. Design for this explicitly:

- **Run profiles** in config: `classroom` (small: a few cases per condition, 1 repetition, reduced context lengths) and `full` (complete evaluation set, configurable repetitions). `--max-cases`, `--repetitions` and `--conditions` CLI overrides, bounded by config maxima.
- **Pre-flight plan for live runs:** before any API call, print the planned number of requests, estimated input tokens (local estimate), largest single request, and estimated cost if verified pricing exists. Abort if the plan exceeds configured limits (`max_requests_per_run`, `max_estimated_tokens_per_run`, `max_input_tokens_per_request`). Require `--yes` to proceed above a configurable confirmation threshold.
- **Client-side rate limiter** honoring configured RPM and TPM, plus retry-after / rate-limit headers when the provider returns them. Requests are sequential by default; optional bounded concurrency.
- Requests whose estimated size exceeds the configured per-request token limit or the model's verified context window are **skipped and reported as skipped**, not counted as failures (relevant to Labs 05 and 06).
- **Token estimation:** use a local estimator only for planning and budget-based context selection. If a suitable open tokenizer for the configured model is available offline (verify; for gpt-oss models, check whether `tiktoken` provides the matching encoding), use it; otherwise use a conservative heuristic and document its error. Always label estimated counts as estimates. **Provider-reported usage is the only source for measured token metrics.** Compare estimate vs. reported in live runs and store the ratio.
- Document in the instructor guide: per-participant keys vs. shared key, the expected rate-limit impact of N concurrent participants, and the recommendation to use replay mode as the default classroom path with optional small live runs.

---

## 8. Shared Core Architecture

Implement under `src/lab_core/`. Use protocols/interfaces where they materially improve testability (the LLM client, the clock, the results sink). Avoid abstractions without a concrete use case.

**Configuration**
- TOML loading into Pydantic models; reject unknown keys; safe defaults (`live_api_enabled = false`).
- Layering: `config/default.toml` < selected `--config` file < CLI overrides. Record the effective config in each run.

**Prompt Builder**
- Builds message arrays from named, versioned templates in `prompts/`.
- Components (instruction, context, constraints, examples, output contract) are represented separately so labs can include or exclude them.
- Untrusted content is wrapped and labeled by the builder and can never be placed in the system message. Enforce this in code and test it.
- Compute a stable `prompt_hash` from the template version and the rendered messages.

**Context Manager**
- Deterministic relevance scoring (e.g. BM25 implemented locally or a small well-known package, with Turkish-aware normalization: casefold with Turkish İ/ı handling, punctuation stripping).
- Deduplication (exact and near-duplicate, e.g. shingle Jaccard with a configurable threshold).
- Freshness filtering via `effective_date` and `superseded_by` metadata.
- Ordering strategies: relevance-descending, relevance-ascending, seeded random, original order.
- Token-budget selection (greedy by relevance under a budget).
- Controlled filler/distractor assembly to a target length with a target fact at a specified relative position.

**Groq Client Adapter**
- Single place for API calls; transport separate from experiment logic.
- Supports `response_format` variants, `reasoning_effort`, and the provider's mechanism for hiding or excluding reasoning text (verify the parameter).
- Normalizes usage metadata (prompt, completion, total, cached, reasoning tokens) **preserving `None` for unreported values**.
- Timeouts; bounded retries with exponential backoff and jitter for retryable errors (429, 5xx, timeouts); no retries for 4xx validation errors.
- Classifies "parameter not supported by this model" errors as `unsupported`, distinct from failures.
- Captures client-side latency and provider timing fields when present.

**Experiment Runner**
- Executes conditions × cases × repetitions with **paired design**: every condition in a comparison runs on the identical case set.
- Seeded counterbalanced ordering of executions to avoid time-of-run confounds.
- Incremental persistence (each observation written as soon as it completes); a crashed run keeps completed observations and records the failure.
- Records every parameter needed for reproduction.

**Evaluation Engine** (deterministic; no LLM-as-judge in the core labs)
- Exact match with documented normalization; label matching against closed sets.
- Classification metrics: accuracy, per-class precision/recall, macro-F1, confusion matrix.
- Instruction-adherence checks defined as explicit, machine-checkable constraints per lab.
- JSON parse check, schema validation, field-level semantic comparison.
- Grounding checks: cited document IDs vs. gold evidence IDs.
- Injection checks: canary tokens and forbidden-action detection.

**Statistics** (Section 10)

**Metrics Collector** — prompt/completion/total/cached/reasoning tokens (as reported), latency, API calls, retries, estimated cost (only with verified, dated pricing; otherwise `null` with reason).

**Results Writer** — layout in Section 12; never overwrites; mode recorded everywhere.

---

## 9. Datasets

### 9.1 General rules

- **Language:** Dataset content (customer messages, policies, documents, questions) is **Turkish**, in a single shared synthetic enterprise domain (e.g. a fictional company's customer support, refund, leave, expense and procurement policies). Code, identifiers, field names and API contracts are English. Record this decision in `docs/decisions.md`, noting that Turkish text affects token counts.
- All data is synthetic. No real persons, companies or personal data. Use obviously fictional names.
- JSON files with a JSON Schema per dataset type in `data/schemas/`. Validation runs as `lab-runner validate-data` and as part of the test suite.
- Stable case IDs; `dataset_version` per file; explicit expected outputs; `metadata` including `difficulty`, `tags` (e.g. `edge_case`, `ambiguous`, `negative`), `source: "synthetic"`, `language: "tr"`.
- Separate splits where examples are drawn: `example_pool` (for few-shot/prompt examples) and `eval`. A leakage check rejects any eval item that is identical or near-duplicate (configurable similarity threshold) to an example-pool item. The check runs in tests.
- Print and test class balance for every classification dataset.

### 9.2 Minimum dataset sizes (eval split)

These are minimums for the `full` profile. The `classroom` profile uses a stratified subset.

| Lab | Minimum eval data |
|---|---|
| 01 | ≥ 60 customer messages, 4–5 classes, ≥ 12 per class, ≥ 15% ambiguous/edge cases; separate example pool ≥ 15 |
| 02 | ≥ 30 refund decision cases with gold decisions; ≥ 20 injection fixtures covering ≥ 5 injection types; ≥ 10 benign control cases that look suspicious but are legitimate (for false-refusal measurement) |
| 03 | ≥ 80 lead messages, 4–5 classes, ≥ 15 per class, ≥ 20% edge cases; example pool ≥ 30, each tagged `typical`, `boundary`, `redundant` or `misleading_candidate` |
| 04 | ≥ 25 questions with gold answers and gold evidence doc IDs; corpus ≥ 40 documents including exact duplicates, near-duplicates, irrelevant documents and ≥ 8 old/new conflicting version pairs |
| 05 | ≥ 20 distinct target facts with questions and gold answers; distractor corpus large enough to reach the largest configured length without repeating identical filler text |
| 06 | ≥ 20 distinct target facts (may share the Lab 05 pool, but runs separately) |
| 07 | ≥ 30 eligibility cases with gold final decisions **and gold intermediate values** (extracted facts, applicable rules, rule outcomes) |
| 08 | ≥ 40 extraction records including missing fields, ambiguous fields, multiple candidate values, and values requiring normalization (dates, amounts, enums) |

If you consider a minimum unjustified for a specific lab, change it, and explain why in `docs/decisions.md`. Do not silently ship fewer.

---

## 10. Statistics and Reporting Rules

Small classroom runs produce noisy numbers. Teaching participants to read that noise is a learning objective.

- Report proportions (accuracy, adherence, parse success, attack success, etc.) with **95% Wilson confidence intervals**.
- Report macro-F1 and between-condition differences with **seeded bootstrap** confidence intervals (configurable resamples, default 1000).
- Because the design is paired, report **per-case flips** between baseline and each treatment: cases that went wrong→right and right→wrong.
- An exact McNemar test may be included and labeled **exploratory**. Do not claim statistical significance in default classroom runs, and never claim it without the test actually being computed.
- With repetitions > 1, report per-case consistency (fraction of repetitions agreeing) and variance across repetitions. Do not assume the API seed guarantees identical outputs.
- Composite scores only when their formula is documented and meaningful.
- Missing values stay missing: `null` plus a reason, never `0`.
- Auto-generated `comparison.md` for each run contains: a mode banner, conditions, n per condition, metrics with CIs, flips, skipped/unsupported counts, and an automatically inserted caution when CIs overlap substantially ("differences within this run may be noise").

---

## 11. Laboratories

### 11.0 Per-lab completion criteria

Each lab directory (`src/labs/labNN_<name>/`) contains its conditions, prompt templates or references, evaluator configuration, and a `README.md`. A lab is complete only when it has:

- learning objective and technical background;
- a testable hypothesis written **before** results, including what result would falsify it;
- independent, dependent and controlled variables, baseline, treatments, dataset, repetitions, evaluation method and threats to validity (also in `docs/experiment-methodology.md`);
- a dataset meeting Section 9.2;
- fixture, replay and live paths through the same pipeline;
- deterministic evaluation, token/latency capture, persistence, `comparison.md`, and charts where useful;
- tests: condition generation, controlled variables held constant across conditions (assert it), expected execution count, evaluator correctness on hand-built cases, persistence;
- participant section (Turkish) and instructor section (Turkish) covering expected-vs-measured distinction, discussion questions, misconceptions and failure modes.

Hold the model and generation parameters (temperature, max tokens, reasoning effort) fixed within each primary comparison. Read them from config and record them.

### LAB 01 — Prompt Anatomy & Instruction Clarity

**Scenario:** Classifying Turkish enterprise customer messages (e.g. `billing`, `technical_issue`, `cancellation`, `complaint`, `general_inquiry`, and a priority field).

**Conditions (cumulative):**
- Baseline: minimal instruction
- A: + context (business background, label definitions)
- B: + constraints (closed label set, no extra text, tie-breaking rule for ambiguous messages)
- C: + output contract (exact format)
- D: + carefully selected examples from the example pool

**Additional controls:**
- **Length control:** a variant of B padded with neutral, task-irrelevant text to match D's token length. This separates "more tokens" from "more useful information".
- **Leave-one-out ablation** (extended profile): the full prompt minus one component at a time.

**Instruction adherence:** define checkable constraints (label within the closed set, no text outside the contract, priority field present, length bound). Report each constraint separately and as an "all constraints met" rate.

**Metrics:** accuracy, macro-F1, per-constraint adherence, format compliance, input tokens, latency, cost per correct response (if verified pricing exists).

**Interpretation point:** more components ≠ automatically better. Show where components help, where they only add tokens, and where they can conflict.

### LAB 02 — Instruction Hierarchy & Untrusted Content

**Scenario:** A corporate refund-decision assistant. Policy (trusted, in system/developer instructions) + customer request + retrieved documents or customer-supplied attachments (untrusted).

**Conditions:**
- Baseline: trusted policy, clean content; measures normal decision accuracy.
- A — naive concatenation: untrusted content containing injected instructions is concatenated into the prompt without labeling.
- B — separated untrusted content: delimited, labeled as data, with an explicit authority statement in the system message.
- C — B + structured decision output + **application-side policy enforcement** (deterministic rule check that can override or block the model's decision).
- D — **direct hierarchy conflict:** the user message itself tries to override the system policy (no injection in documents). Tests system-vs-user precedence directly.

**Injection fixtures:** synthetic and harmless. Cover at least: instruction override, fake role/authority markers (e.g. a fake "SYSTEM:" block), fake policy update, hidden or obscured instructions (e.g. HTML comments, unusual formatting), and a system-prompt-disclosure attempt detected via a **canary token** placed in the system message.

**Metrics — measured at two levels, reported separately:**
- **Model-level attack success rate:** the model's raw output follows the injected goal (or leaks the canary).
- **System-level attack success rate:** the final action after application enforcement follows the injected goal.
- Policy decision accuracy on benign cases, **false refusal rate** on benign controls, escalation/"needs human review" rate.

**Interpretation point:** prompt formatting is not a security boundary. Condition C may reduce system-level success while model-level success stays high. The model is still manipulated; only the effect is contained. This is defense in depth, not a fix.

### LAB 03 — Few-Shot Example Engineering

**Scenario:** Turkish B2B lead classification (e.g. `hot`, `warm`, `cold`, `not_a_lead`, `partner_inquiry`).

Two separate experiment series, so that **count** and **quality** are never varied at the same time:

**Series 1 — Count** (fixed selection strategy: diverse + boundary, class-balanced): 0, 2, 4, 8 examples.

**Series 2 — Quality at fixed k = 4** (class-balanced unless the condition is about imbalance):
- random from the pool (seeded, several seeds)
- redundant (near-identical examples)
- diverse-typical (prototypical examples per class)
- **boundary-focused / ambiguity-reducing** (examples near decision boundaries that disambiguate commonly confused classes, selected from the confusion pattern of the zero-shot run or from `boundary` tags)
- misleading (examples with a spurious surface cue correlated with the wrong label; and/or mislabeled examples, clearly documented)

**Optional:** example order effect (same 4 examples, different orders).

**Metrics:** accuracy, per-class precision/recall, macro-F1, confusion matrix, edge-case accuracy, input tokens, tokens per correct classification.

Enforce the leakage check between example pool and eval split.

**Interpretation point:** which examples matter more than how many. Boundary examples should help specifically on the confused class pairs. Check the confusion matrix, not only the headline accuracy.

### LAB 04 — Context Selection, Budget, Ordering & Freshness

**Scenario:** Internal corporate policy Q&A over the synthetic corpus. Answers must cite document IDs.

**Conditions:**
- All documents (if this exceeds the per-request limit, cap it and document the cap)
- Relevance-filtered (top-k by deterministic scoring)
- Relevance + deduplication
- Relevance + deduplication + freshness (superseded versions removed)
- **Budget series:** greedy relevance selection under several token budgets (configurable)
- **Ordering:** the same selected set (relevance + dedup + freshness) ordered relevance-descending vs. relevance-ascending vs. seeded random

**Metrics:**
- **Selection-level** (no LLM needed): evidence recall and precision of the selector against gold evidence IDs, stale-document inclusion rate. Teach that a selector failure bounds answer quality.
- **Answer-level:** grounded answer accuracy, citation correctness, stale-answer rate (answer reflects the superseded policy), context tokens, budget utilization, cost per correct answer.

**Interpretation point:** distinguish "the right evidence was not in the context" from "the evidence was there but the model did not use it".

### LAB 05 — Context Rot

**Scenario:** Extracting specific facts from long enterprise documents.

**Independent variable:** total context length. Default configurable list approximately 1K, 4K, 8K, 16K, 32K tokens. Lengths that exceed config limits, the verified context window or rate limits are skipped and reported.

**Controlled:** the same target facts at every length; the target fact's relative position fixed (or balanced across the same set of positions at every length); distractor type and density fixed; question wording fixed. Filler is coherent synthetic enterprise text, not lorem ipsum or repeated blocks. Include a fixed proportion of near-miss distractors (similar facts with different values) at every length.

**Answering contract:** the model must answer or return an explicit "not found" token.

**Metrics:** accuracy, exact match, unsupported/hallucinated answer rate (an answer not present in the context), "not found" rate, reported input tokens, latency, degradation relative to the shortest length (with CIs).

**Interpretation point:** report the actual curve. It may be flat at the tested lengths for this model and task. That is a valid finding and should be discussed, not hidden.

### LAB 06 — Lost-in-the-Middle

**Scenario:** Retrieving a relevant policy clause from a long document.

**Independent variable:** relative position of the target (beginning, middle, end; optionally 5 positions: 0%, 25%, 50%, 75%, 100%).

**Controlled:** **fixed total length** (configurable, default moderate, e.g. ~8K tokens); identical filler across positions; the same set of target facts at every position; counterbalanced permutations so that each fact appears in each position.

Keep Lab 06 separate from Lab 05: Lab 05 varies length at fixed position, Lab 06 varies position at fixed length. State this in both READMEs.

**Metrics:** accuracy by position, exact match, evidence identification (the model reports the clause ID it used), latency.

**Interpretation point:** the effect varies by model, length and task. A weak or absent effect is a legitimate result.

### LAB 07 — Reasoning Guidance & Task Decomposition

**Scenario:** Policy-based eligibility and approval decisions (e.g. expense or leave approval with multiple rules and thresholds).

**Important confound:** `gpt-oss` models are reasoning models. They reason internally even under a "direct answer" prompt. The primary comparison is therefore **external task structuring vs. relying on the model's internal reasoning**, not "reasoning vs. no reasoning". Explain this in the lab README and the instructor guide.

**Primary comparison** (`reasoning_effort` held fixed at a configured value):
- Direct answer: final decision only.
- Single-call structured guidance: explicit steps; the output contract includes intermediate fields (extracted facts, applicable rules, rule outcomes, decision).
- Multi-call decomposition: extract facts → determine applicable rules → evaluate → decide, with explicit intermediate outputs passed between calls.
- Multi-call + validation: as above, plus a **deterministic application-side validator** that checks intermediate outputs against the rules and triggers at most one bounded re-ask on inconsistency.

**Secondary experiment:** `reasoning_effort` sweep (verified supported values) on the direct-answer condition only.

**Metrics:** end-to-end accuracy, intermediate step accuracy (against gold intermediate values), API calls, input/output tokens, reasoning tokens when reported, total latency, estimated cost.

**Rules:** do not request, store, display or evaluate hidden reasoning text. If the API returns reasoning text by default, configure it to be hidden/excluded where supported, or discard it before persistence and record that it was discarded. Evaluate only explicit outputs.

**Interpretation point:** decomposition buys auditability and intermediate validation, at a cost in calls, tokens and latency. It does not necessarily improve final accuracy for a capable reasoning model.

### LAB 08 — Structured Outputs & JSON Schema

**Scenario:** Extracting structured data from Turkish customer requests (customer reference, request type enum, amount and currency, dates, product, urgency, optional/nullable fields, a nested object).

**Conditions:**
- Plain natural-language instruction (no JSON requested), evaluated by a lenient parser to show the gap
- Prompt-only "Return JSON"
- Provider JSON Object Mode
- JSON Schema, best-effort mode
- JSON Schema, strict mode

Verify which modes and schema features the selected model supports. Unsupported modes or features are reported as **unsupported/skipped**, never as quality failures. Design the schema within the verified strict-mode feature limits and document any feature you had to avoid.

**Metrics — three separate layers:**
1. JSON parse success
2. Schema adherence (application-side `jsonschema` validation, **always** performed, even in strict mode)
3. Semantic accuracy: per-field correctness against gold values with documented normalization; required-field correctness; correct use of `null` for missing information vs. hallucinated values

Plus API errors, retries, tokens, latency.

**Interpretation point:** Valid JSON ≠ schema-compliant JSON ≠ semantically correct data. Strict mode guarantees layer 2 at most, never layer 3.

---

## 12. Results, Reports and Visualization

Layout:

```text
results/
└── lab01/
    └── 2026-11-02T10-15-30Z_live_a1b2c3/        # timestamp_mode_shortid
        ├── run.json             # run metadata, effective config, model, versions, git commit if available
        ├── observations.jsonl   # one line per execution
        ├── summary.json         # aggregated metrics with CIs
        ├── comparison.md        # human-readable report (Section 10)
        └── charts/*.png
```

Each observation includes: experiment ID, lab ID, run ID, condition ID, case ID, repetition, execution mode, timestamp, model ID, generation parameters, prompt template version, prompt hash, dataset version, raw response (and, for replay, the source run ID), expected output, evaluation results, reported usage (with `null`s preserved), latency, retries, error or skip reason.

Priority charts (actual observed data, with CI error bars where applicable): baseline vs. treatment accuracy (Lab 01), instruction adherence (Lab 01), model- vs. system-level attack success (Lab 02), few-shot quality vs. tokens (Lab 03), selection recall and answer accuracy vs. budget (Lab 04), length vs. accuracy (Lab 05), position vs. accuracy (Lab 06), decomposition accuracy vs. cost (Lab 07), three-layer structured-output results by mode (Lab 08).

Every chart in fixture mode carries a visible "SIMULATED" watermark or title prefix. Never mix modes in one chart.

`lab-runner report <run_dir>` regenerates summary, comparison and charts from an existing run.

---

## 13. Configuration & API Safety

Provide `config/default.toml` (fixture mode, live disabled), `config/live.example.toml`, `config/classroom.example.toml`, and `.env.example`. `.gitignore` excludes `.env`, `config/live.toml`, `config/classroom.toml`, and `results/` (except a `.gitkeep`). `data/recordings/` is committed.

Live execution requires **both** `execution.live_api_enabled = true` in the selected config **and** `--live` on the command line. A missing key produces a clear error before any request. Test that no code path can reach the network in fixture or replay mode (the fake client is injected, and the real client refuses construction when live is not authorized).

Also: max cases, max repetitions, per-request and per-run token limits, request timeout, bounded retries with backoff and jitter, capability checks, optional pricing with `verified_at` and `source_url`. If pricing is missing or unverified, cost is `null` with a reason.

---

## 14. Testing

The normal suite (`uv run pytest -q`) needs no credentials and no network. Live tests live under `tests/live/`, are marked `@pytest.mark.live`, and are skipped unless explicitly selected and authorized.

Required coverage:

- **Unit:** config validation (including unknown keys), prompt building (untrusted content never in the system message; prompt hash stability), context manager (relevance, dedup, freshness, ordering, budget, position placement, target length accuracy), dataset loading and schema validation, leakage check, evaluators on hand-built cases, statistics (Wilson, bootstrap determinism with a seed, flips), usage normalization preserving `None`, results writer (no overwrite, incremental writes).
- **Lab:** condition generation, controlled variables constant across conditions, expected execution counts, paired case sets, end-to-end fixture run per lab.
- **Integration:** CLI → runner → fake client → evaluation → persistence → report; replay of the synthetic recording fixture; prompt-drift detection in replay; failed and partial runs persisted correctly.
- **Safety:** no network in fixture/replay; missing API key; `--live` without config opt-in and vice versa; unsupported capabilities classified as unsupported; invalid JSON and schema violations; malformed datasets; retry exhaustion; pre-flight limit abort.

Also: `ruff check` and `ruff format --check` pass. Docker smoke via `scripts/smoke.ps1` / `scripts/smoke.sh` (Section 6).

**Live smoke procedure:** `docs/live-smoke.md` plus a command that sends one minimal request per lab with the classroom profile. Run it only if a key is available, and record the actual outcome. Never report it as passed otherwise.

Mocks test orchestration and evaluation logic; they are not evidence of model accuracy. State this in the README.

---

## 15. Documentation

```text
README.md
CHANGELOG.md
docs/spec.md                     # this document
docs/project-context.md
docs/decisions.md
docs/architecture.md
docs/groq-capabilities.md        # verified facts with URLs and access dates
docs/experiment-methodology.md
docs/statistics.md               # CIs, bootstrap, flips, why small runs are noisy
docs/tasks.md
docs/verification-log.md
docs/live-smoke.md
docs/participant/README.md       # Turkish
docs/instructor/README.md        # Turkish
src/labs/labNN_*/README.md       # per-lab, Turkish explanations, English identifiers
data/recordings/README.md        # instructor procedure for producing replay sources
```

- Code, identifiers, API contracts and architecture docs: English.
- Participant and instructor guides and lab READMEs: Turkish, keeping established technical terms in English.
- **Participant guide:** setup, Docker commands (PowerShell), Groq key configuration, the three modes and when to use each, running each lab, reading `comparison.md` and JSON results, reading CIs and flips, reflection questions per lab, troubleshooting (including Windows-specific issues).
- **Instructor guide:** per-lab technical explanation, learning outcomes, hypotheses, suggested demo flow, **expected observations clearly separated from measured results**, discussion questions, misconceptions, failure modes, how to produce replay recordings before the session, rate-limit and key-distribution guidance, and a suggested time plan with labs marked **core** or **extended**. Suggested default: core = 01, 02, 03, 04, 08; Labs 05 and 06 as one combined demo; Lab 07 extended. Make this configurable and easy for the instructor to change.
- Every command in the docs must correspond to an implemented feature and be verified (or explicitly marked Not Verified).

---

## 16. Project Structure (starting point; justified changes allowed)

```text
llm-prompt-engineering-lab/
├── config/
│   ├── default.toml
│   ├── live.example.toml
│   └── classroom.example.toml
├── data/
│   ├── schemas/
│   ├── golden/            # per-lab eval and example-pool datasets
│   ├── contexts/          # policy corpus, distractor corpus
│   ├── fixtures/          # fixture-mode response fixtures (labeled simulated)
│   └── recordings/        # instructor-produced live runs for replay (README only initially)
├── prompts/
│   ├── templates/
│   └── examples/
├── scripts/
│   ├── smoke.ps1
│   └── smoke.sh
├── src/
│   ├── lab_core/
│   │   ├── cli.py
│   │   ├── config.py
│   │   ├── groq_client.py
│   │   ├── fake_client.py
│   │   ├── replay.py
│   │   ├── rate_limiter.py
│   │   ├── tokens.py
│   │   ├── prompt_builder.py
│   │   ├── context_manager.py
│   │   ├── experiment_runner.py
│   │   ├── evaluation.py
│   │   ├── statistics.py
│   │   ├── metrics.py
│   │   ├── reporting.py
│   │   └── results_writer.py
│   └── labs/
│       ├── lab01_prompt_anatomy/
│       ├── lab02_instruction_hierarchy/
│       ├── lab03_few_shot/
│       ├── lab04_context_selection/
│       ├── lab05_context_rot/
│       ├── lab06_lost_in_middle/
│       ├── lab07_task_decomposition/
│       └── lab08_structured_outputs/
├── tests/
│   ├── core/
│   ├── labs/
│   ├── integration/
│   ├── live/
│   └── fixtures/
├── docs/ (see Section 15)
├── results/.gitkeep
├── .dockerignore
├── .env.example
├── .gitattributes
├── .gitignore
├── .python-version
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── uv.lock
├── README.md
└── CHANGELOG.md
```

Use a proper `src` layout so imports work identically locally and in Docker. Expose the CLI as a project script (`lab-runner`).

---

## 17. Quality Standards

Separation of concerns; type hints throughout; meaningful exceptions; dependency injection for the client, clock and randomness; minimal duplication; clear names; deterministic tests; secure secret handling; graceful failure; reproducible dependencies. Prefer readable, auditable code over volume. The target reader is an intermediate-to-advanced Python / AI Engineering participant who should be able to open any lab and follow the data flow from dataset to report.

---

## 18. Definition of Done

Mark each item **Passed**, **Failed** or **Not Verified (reason)** in the final report, with a pointer to the evidence in `docs/verification-log.md`.

**Infrastructure**
- [ ] `uv sync --frozen` succeeds; `uv.lock` committed
- [ ] Docker image builds; Compose CLI works; `list` shows all eight labs
- [ ] Config and data changes take effect without rebuild
- [ ] No secrets committed or embedded in the image

**Labs**
- [ ] All eight labs meet the per-lab completion criteria (11.0)
- [ ] Each lab runs in fixture mode locally and in Docker
- [ ] Replay mode works (verified on the synthetic recording fixture)
- [ ] Each lab has a live path; live verified per lab or marked Not Verified
- [ ] Datasets meet Section 9.2 minimums (or deviations are justified in decisions.md)

**Evaluation**
- [ ] Dataset schemas and leakage checks pass
- [ ] Paired design enforced; controlled variables asserted in tests
- [ ] CIs and flips reported; no unsupported significance claims
- [ ] Reported usage preserves `null`; estimates labeled as estimates
- [ ] Fixture/replay/live clearly distinguished in data, reports and charts

**Testing**
- [ ] Offline suite passes (report counts)
- [ ] ruff check and format check pass
- [ ] Docker smoke scripts pass
- [ ] Safety tests pass (unauthorized live blocked, no network in offline modes)

**Documentation**
- [ ] All documents in Section 15 exist and are complete
- [ ] Documented commands verified
- [ ] Known limitations stated

---

## 19. Final Delivery Report (in Turkish)

1. Repository summary
2. Architecture summary
3. Lab status table (8 rows: fixture / replay / live / tests / docs / dataset size)
4. Docker verification — commands actually executed and outcomes
5. Test results — counts, failures found, fixes made
6. Groq API verification — which real calls succeeded, if any
7. Evaluation and statistics capabilities
8. Documentation status
9. Deviations from this spec and why
10. Known limitations and unverified items
11. Getting started — exact PowerShell commands for a participant, and the instructor's pre-training recording procedure

Report evidence, not assumed success. Passing unit tests is not production readiness. Do not push to any remote.

---

## 20. Start

Save this document as `docs/spec.md`, then begin **M0**. Proceed through M2 without asking for approval, then stop at the checkpoint and report in Turkish.

Priorities, in order: technical correctness, experimental validity, educational value, reproducibility, Docker usability, maintainability, documentation quality.
