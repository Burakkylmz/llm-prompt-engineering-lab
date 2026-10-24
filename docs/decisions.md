# Architecture & Design Decisions

Append-only log. Each entry: date, decision, rationale, alternatives considered.

## 2026-10-24 — Reference repository analysis

Both reference repositories were cloned and read directly (not guessed from memory):
- `https://github.com/Burakkylmz/llm-token-economics-lab` (primary reference)
- `https://github.com/Burakkylmz/llm-sampling-lab` (secondary reference)

**Adopted from `llm-token-economics-lab`:**
- The `src/lab_core/` + `src/labs/labNN_<name>/` split, with each lab exposing `LAB_ID` and a `register(subparsers)` function; the root CLI discovers labs by an **explicit hardcoded list** of module paths (not a filesystem scan), so a half-written lab directory is never picked up accidentally. We keep this pattern exactly — `src/lab_core/cli.py` hardcodes the 8 lab modules.
- The `--live` + `config.execution.live_api_enabled` double-gate pattern (`lab_cli_support.build_context`), including: `LiveExecutionNotAllowed` raised (not silently downgraded) when `--live` is passed without the config opt-in, and a cost-warning line printed before any live call. We extend this with the spec's additional requirement that the *fake client* is injected by default and the *real client's constructor itself* also refuses to build when live is not authorized (defense in depth at two layers, not just the CLI layer) — see `src/lab_core/groq_client.py`.
- `TokenCostMetrics`/`PerformanceMetrics`-style dataclasses that default every provider-reported numeric field to `None` and normalize defensively via `getattr`, never fabricating `0`. We carry this principle into `src/lab_core/metrics.py` and `src/lab_core/groq_client.py` verbatim as a design rule.
- TOML config loaded into a frozen dataclass tree with a `_require()` helper that raises `ConfigError` on missing keys. We generalize this into Pydantic models instead (spec Section 4 mandates Pydantic), which gives us "reject unknown keys" via `model_config = {"extra": "forbid"}` for free instead of hand-written presence checks — a direct improvement, not a deviation.
- Dockerfile shape: `uv sync --frozen --no-install-project` first (dependency layer caches independently of source changes), then copy source and `uv sync --frozen` again. Adopted as-is for `Dockerfile`, with the spec's additional requirement of a non-root user and `.gitattributes`-forced LF line endings for Windows/Docker Desktop compatibility.
- Exponential-backoff-with-jitter as a standalone, policy-free helper function (`compute_backoff_delay_seconds`), deliberately not auto-wired into the client, so retry behavior stays an explicit, testable decision at the call site. Adopted into `src/lab_core/rate_limiter.py`, extended to also honor a provider `retry-after` header when present (per spec Section 7).

**Adopted from `llm-sampling-lab`:**
- Fewer directly-reusable patterns (it is single-package rather than shared-core/multi-lab), but its `settings.toml` validation style (explicit per-section, per-field checks with descriptive `ValueError` messages) confirmed the value of fail-fast, explicit config validation, which we now get more cheaply via Pydantic validators.
- Its `tests/conftest.py`-style fake-client factories (a class that mimics only the attribute shape the production code actually reads, recording calls for assertions) is the model for this project's `FakeGroqClient` in `src/lab_core/fake_client.py`, extended to support **labeled fixture-file-driven** and **deterministic-rule-driven** responses (this project's fixture mode is richer than either reference repo's: it must serve a whole evaluation pipeline, not just return canned text).

**Changed, and why:**
- **Pydantic instead of hand-rolled dataclasses + `_require()`** for config (spec-mandated; also gives "reject unknown keys" and declarative range/type validation for free).
- **`jsonschema` for dataset/schema validation** — neither reference repo needed this (they don't validate structured datasets), so this is new, not a deviation from a prior pattern.
- **Three execution modes (fixture / replay / live) instead of two (simulated-flag / `--live`).** Neither reference repo has a replay mode. This is this project's architectural novelty per spec Section 2 and is designed fresh in `docs/architecture.md`.
- **Evaluation Engine, Statistics module (Wilson CI, bootstrap, McNemar, flips), Context Manager, Prompt Builder** are all new — the reference repos measure token/cost/latency/sampling behavior, not prompt-quality or context-engineering outcomes. This project's "Prompt Quality Evaluation Engine" is the other architectural novelty called out in spec Section 2.
- **argparse retained** (not Typer) to stay consistent with the reference repos' CLI style and avoid adding a dependency without clear value, per spec Section 4's "add other dependencies only with clear value" rule.

## 2026-10-24 — Dataset language

All dataset *content* (customer messages, policy documents, questions, lead messages, expense/leave cases) is written in **Turkish**, per spec Section 9.1. Code, field names, JSON keys, and all documentation in `docs/*.md` (except participant/instructor guides and per-lab READMEs) are English. This is a deliberate asymmetry: the training audience is Turkish-speaking, but the codebase must remain readable by anyone reviewing or maintaining it.

**Consequence recorded for later labs:** Turkish text is denser per token than English under BPE-style tokenizers (agglutinative morphology, diacritics) — this affects every token-budget calculation in Lab 04 (context budgets), Lab 05 (context-rot lengths), and Lab 06 (fixed-length filler). The local token estimator (`src/lab_core/tokens.py`) uses a Turkish-specific chars-per-token ratio for this reason (see `docs/groq-capabilities.md` Section 6), and all token-length *targets* in dataset generation are expressed as "generate until the estimator says length L," then corrected against **provider-reported** tokens once a live/replay run exists, never assumed equal to the English heuristic.

## 2026-10-24 — Pricing & capability verification

Pricing for `openai/gpt-oss-20b` ($0.075/1M input, $0.30/1M output) was confirmed directly from `https://console.groq.com/docs/model/openai/gpt-oss/20b` on 2026-10-24 — a first-party Groq page, fetched live, not a third-party tracker (the reference `llm-token-economics-lab` repo explicitly flagged its own pricing numbers as third-party-sourced and unconfirmed against Groq's own page; this project improves on that by using a confirmed first-party source for the default model). Cached-input pricing for this model was **not found** on the fetched page and is recorded as unverified (`null` + reason) rather than guessed or copied from a third-party tracker. See `docs/groq-capabilities.md` for the full capability/pricing verification record.

## 2026-10-24 — M2 architecture notes

- **`context_manager.py` deferred to M3.** Spec Section 8 lists it under the shared core
  architecture, but Lab 01 (prompt anatomy) does no document retrieval, relevance scoring, or
  budget-based selection at all — its "context" component is one fixed, static business-
  background block. Building context_manager.py now, with no lab exercising it and no
  realistic test data to validate it against, would mean shipping untested code or writing
  throwaway tests against synthetic inputs invented purely for the exercise. It is built in
  M3 as part of Lab 04, which is the first lab that actually needs relevance scoring,
  deduplication, freshness filtering, ordering, and budget selection — at that point it can
  be built and tested against Lab 04's real policy-corpus dataset.
- **`text_similarity.py` extracted as shared infrastructure**, not folded into
  `datasets.py` alone, because the spec's Section 8 Context Manager also needs shingle-
  Jaccard near-duplicate detection for Lab 04's document deduplication. One implementation
  (`shingle_jaccard`) now serves the M2 eval/example-pool leakage check and will serve M3's
  document dedup — avoiding writing the same similarity logic twice.
- **Lab 01's dataset was generated by a template-filling script** (not hand-typed one row at
  a time, and not downloaded from any source): fixed Turkish sentence templates per class,
  with product/order-number/date/amount slots filled from small curated lists, run with a
  fixed seed. The script itself was not committed (it is a one-off authoring tool, not part
  of the shipped pipeline); its output — `data/golden/lab01/eval.json` and
  `example_pool.json` — is the dataset of record, reviewed for realism and uniqueness
  (a programmatic leakage/collision check was run as part of generation and again by
  `tests/labs/test_lab01_dataset.py`). This is disclosed here per the spec's honesty rules:
  the data is synthetic by design (Section 9.1 requires this), generated with templates
  rather than invented free-hand, which is why it reads as somewhat formulaic — that is an
  accepted tradeoff for guaranteed class balance, leakage-freedom, and reproducibility.
- **Lab 01's evaluator checks the strict two-line format on *every* condition**, including
  conditions whose prompt never asked for it. This was a deliberate design choice, not an
  oversight: it is what makes the instruction-adherence comparison meaningful (baseline/A/B
  are *expected* to score low on `format_compliant`, because strict formatting was never
  requested until condition C). This is spelled out in Lab 01's README so a participant
  does not mistake a low baseline format-compliance score for a bug.
- **Self-review caught a missing required feature:** the Section 7 pre-flight plan for live
  runs was absent from Lab 01's CLI until a review pass before the M2 checkpoint. It has
  since been implemented (`src/lab_core/preflight.py`) and wired in; see
  `docs/verification-log.md`'s M2 entry for the fix record. Flagging this here rather than
  silently folding it into the "M2 work" to be transparent that the first pass of M2 was
  incomplete against the spec and required a deliberate gap-check against Section 7 before
  calling M2 done.

## 2026-10-24 — M3 Lab 02 design notes

- **Core extension: `Condition.build_user_input`.** Lab 01's conditions are all
  case-independent (the same static `PromptComponents` for every case; only `case.input_text`
  varies). Lab 02 needs per-case untrusted content (an attached "document," or a
  direct-conflict override appended to the user's own message) — the existing
  `ExperimentRunner._execute_one` had no hook for this. Added an optional
  `build_user_input: Callable[[Case], tuple[str, tuple[UntrustedBlock, ...]]]` field to
  `Condition`, defaulting to `None` (-> `case.input_text` verbatim, no untrusted blocks),
  which is exactly Lab 01's existing behavior — confirmed non-breaking by re-running Lab 01's
  full test suite before building on it further.
- **A/B/C each split into an injection-case and a benign-control condition_id**, rather than
  mixing both case types under one condition_id. The generic `reporting.summarize_condition`
  computes each check's rate over *all* observations in a condition_id; mixing injection cases
  (where `model_level_attack_success` is meaningful) with benign controls (where it is always
  absent/false) would dilute the attack-success rate with structurally-irrelevant
  denominator entries. Splitting keeps every rate's denominator homogeneous and meaningful,
  and required no changes to the generic reporting pipeline at all — it already handles an
  arbitrary number of condition_ids and arbitrary per-observation check keys.
- **Condition C's enforcement is a narrow bright-line check** (deny any model "approve" on a
  case where trusted order data already makes denial unambiguous — not defective, >30 days
  old), not a full re-derivation of the gold decision from scratch. This was a deliberate
  choice: a full re-derivation would make condition C trivially always-correct, which would
  not teach anything (and would misrepresent real application-side guardrails, which are
  typically narrow, specific checks, not an independent full policy engine re-running on
  every call). The narrower check still produces the spec's intended teaching contrast
  (model-level attack success stays high, system-level drops) while leaving open, honestly,
  that subtler attacks on genuinely ambiguous cases might still slip through C — recorded in
  Lab 02's README as the relevant interpretation point.
- **Fixture-mode resolver simulates a maximally-vulnerable fake model** (complies with any
  detected override, discloses the canary whenever asked), rather than Lab 01's
  "always echo gold" rule. This was necessary for the fixture-mode report to show *any*
  nonzero attack-success signal at all (a perfectly compliant/gold-echoing fixture would show
  0% attack success everywhere, which would not exercise — or let a participant inspect —
  the model-level-vs-system-level computation this lab exists to teach). This is disclosed
  prominently in `fixtures.py`'s docstring and the lab's README precisely because it is a
  stronger, more deliberate fictionalization than Lab 01's, and must not be mistaken for a
  claim about real model vulnerability.

## 2026-10-24 — M3 Lab 03 design notes

- **Fixture mode cannot demonstrate either axis of this lab's actual hypothesis.** Unlike
  Lab 01/02, where the fixture resolver's deterministic rule could be made to depend on the
  active condition (format-contract presence, injection-marker presence), Lab 03's dependent
  variable (does the number/quality of examples change accuracy) has no analogous
  condition-visible signal for a fixture resolver to key off honestly — the only honest
  fixture behavior is "always return the gold label," which necessarily shows 100% accuracy
  in every condition. This is stated plainly in Lab 03's README rather than built around with
  an artificial-but-differentiated fixture rule (which would risk being mistaken for a
  real finding). The token-count axis of the "quality vs. tokens" chart is still real and
  differentiated even in fixture mode, since it reflects the actual rendered prompt length.
- **Bug found and fixed:** `wilson_ci`'s bounds could land a floating-point epsilon outside
  `[low, point_estimate]`/`[point_estimate, high]` at proportions of exactly 0 or 1 (which
  Lab 03's fixture mode hits in every single condition, unlike Labs 01/02 which had at least
  one condition below 100%). Fixed by clamping both bounds to contain the point estimate;
  see `docs/verification-log.md`'s M3 (Lab 03) entry for the fix record and regression test.
- **Example-count series is capped by the pool's actual typical+boundary supply** (15 + 8 =
  23 candidates), comfortably above the `count_8` requirement; not an issue at this pool
  size, but documented since a smaller pool would need `select_diverse_boundary` to either
  degrade gracefully (it does — see `_round_robin_by_label`, which simply stops producing
  fewer than `k` examples once the candidate pool is exhausted) or raise, and this project
  chose graceful degradation over raising.

## 2026-10-24 — M3 Lab 04 design notes

- **`context_manager.py` built as planned** (deferred from M2 to M3 specifically for this
  lab — see the earlier M2 entry). BM25 (k1=1.5, b=0.75) was chosen over a simpler TF-IDF
  cosine similarity because it is the standard, well-understood baseline for lexical
  retrieval and is simple enough to implement and unit-test from scratch without a new
  dependency, consistent with spec Section 4's "add dependencies only with clear value."
- **Selection-level metrics are computed directly, bypassing the Observation/evaluation
  pipeline entirely** (a dedicated `selection_metrics.py`, called once per report, not once
  per observation). This matches the spec's explicit framing ("no LLM needed") and avoids a
  design that would otherwise require threading "which documents were actually selected"
  through to the evaluator — which, after Lab 02's `build_user_input` extension, *could*
  have been done by stuffing document IDs into `case.metadata` per-condition, but that would
  require either a different `Case` object per condition (breaking the paired-design
  invariant that one `cases` list is shared across conditions) or a second core extension.
  Computing selection metrics directly from each condition's selector function, independent
  of any run, avoided both problems and is honestly simpler.
- **Answer-level evaluation deliberately does not know what was actually selected** — it
  only compares the model's stated answer/citation against the question's gold fields
  (`gold_answer`, `gold_evidence_doc_ids`, `stale_value`, `stale_doc_id`). This was checked
  to be sufficient: "stale answer" is an outcome property (did the output match the old
  value), not something that requires knowing the prompt's actual content.
- **Bug found and fixed:** `filter_fresh`'s set-difference logic was inverted — see
  `docs/verification-log.md`'s M3 (Lab 04) entry. Caught immediately by a hand-built unit
  test (`_doc("old", ..., superseded_by="new")` / `_doc("new", ...)`) before any
  dataset-scale test could have masked it by accident.
- **Near-duplicate corpus entries use single-word edits, not full paraphrases**, after an
  initial attempt at fuller paraphrasing scored far below the dedup threshold (0.08–0.2
  shingle-Jaccard similarity for a ~25-word sentence with several words changed, because
  5-word shingles are sensitive to edits in short texts). This is recorded as a real
  property of the shingle-Jaccard method at this `k`, not papered over: a realistic
  near-duplicate detector would need either a smaller `k`, a different similarity measure,
  or acceptance that only close edits are reliably caught — this project chose the third,
  documented option rather than silently loosening the threshold to make weakly-similar
  pairs pass.

## 2026-10-24 — M4 Lab 05 design notes

- **Filler pool built combinatorially** (subject x period x activity sentence templates,
  deduplicated via a `set`) to reach 2,300 distinct sentences (~44,800 estimated tokens)
  comfortably above the largest tested length (32,000 tokens) — so the spec's "without
  repeating identical filler text" requirement is met for real, not approximately. An
  assertion in the generator itself verifies no fact's exact sentence leaks into the filler
  pool (which would corrupt the controlled single-needle design).
- **Length-exceeds-limit skip logic lives in the lab's own `cli.py`, not in
  `ExperimentRunner`.** The runner has no concept of "this specific condition is too large
  to attempt" — that is a property Lab 05 knows ahead of time (the target length is fixed
  per condition_id), so excluding those conditions from the real run and directly
  constructing skip `Observation`s for them (bypassing the runner for those items only) was
  simpler than adding a new core capability for a need only this lab currently has.
- **The three-stage fixture degradation rule (correct / confused-by-near-miss / not-found)
  uses fixed, arbitrary token thresholds** (5,000 / 18,000) chosen only to produce a
  non-trivial, inspectable curve in SIMULATED mode. These thresholds have no connection to
  any real model's actual behavior and are documented as such in the lab's README's
  "Instructor Notes" section, to head off a participant mistaking the fixture-mode chart's
  shape for a real finding.

## 2026-10-24 — No dataset-minimum deviations in M0–M2

No deviation from the Section 9.2 minimum dataset sizes was needed for Lab 01 (the only lab built through the M2 checkpoint). Lab 01's dataset meets or exceeds: ≥60 eval messages, 5 classes, ≥12/class, ≥15% ambiguous/edge-case tagged, example pool ≥15. See `src/labs/lab01_prompt_anatomy/README.md` for the exact counts once generated, and `docs/verification-log.md` for the test that asserts class balance.
