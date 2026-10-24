# Experiment Methodology (draft, M0)

> Draft during M0; filled in with per-lab detail as each lab is built (M2–M4). Lab 01's
> section below is final as of M2.

## Shared principles across all 8 labs

- **Paired design.** Every condition in a comparison is evaluated on the identical case set,
  in the same run, so differences are attributable to the manipulated variable rather than to
  a different sample of cases.
- **Hypothesis before results.** Each lab's README states a falsifiable hypothesis before any
  run happens, plus what observed result would falsify it.
- **Controlled variables are asserted, not assumed.** Model ID, temperature, max_tokens,
  reasoning_effort (where applicable) are fixed within a primary comparison and a unit test
  asserts that every condition's generated request parameters are identical except for the
  deliberately-varied prompt/context content.
- **Deterministic evaluation.** No LLM-as-judge. Every metric is computed by code that can be
  read, tested on hand-built cases, and re-run identically in replay mode.
- **Uncertainty is reported, not hidden.** Wilson CIs on proportions, bootstrap CIs on
  macro-F1/differences, per-case flips for paired comparisons. McNemar's test is included as
  exploratory only, never as a significance claim in default classroom-sized runs.
- **Three evidential tiers.** fixture (pipeline test only) < replay (real model behavior,
  recorded) ≤ live (real model behavior, fresh). Every artifact states which tier produced it.

## Lab 01 — Prompt Anatomy & Instruction Clarity

**Scenario:** classify a Turkish enterprise customer-support message into one of 5 closed
classes (`billing`, `technical_issue`, `cancellation`, `complaint`, `general_inquiry`) plus a
`priority` field (`low`/`medium`/`high`).

**Hypothesis:** adding prompt components in the order instruction → context → constraints →
output contract → examples monotonically improves accuracy and instruction adherence, **but**
the improvement is driven by the *information* each component adds, not merely by the extra
tokens it costs. **Falsified if:** the length-matched neutral-padding control (condition
`B_len`) scores within the treatment's own run-to-run noise band of condition D (examples),
despite D having far more task-relevant tokens — that would show tokens, not information,
drove the gain. Also falsified if accuracy does not improve monotonically baseline→A→B→C and
no component-conflict explains a regression.

**Independent variable:** prompt component set (6 conditions: `baseline`, `A_context`,
`B_constraints`, `B_len` [length-matched neutral-padding control], `C_output_contract`,
`D_examples`).

**Dependent variables:** accuracy, macro-F1, per-constraint adherence rate, "all constraints
met" rate, input tokens (reported), latency (reported), cost per correct response (if pricing
verified for the active model).

**Controlled:** model ID, `temperature`, `max_tokens` fixed and identical across all 6
conditions (asserted by `tests/labs/test_lab01.py::test_controlled_params_identical`); dataset
(same 60+ eval cases for every condition); repetitions (config-driven, default 1 for
`classroom`, 3 for `full`).

**Baseline:** condition `baseline` — a one-line instruction with no context, constraints,
output contract or examples; classification parsed leniently (first matching label token in
free text). This is the floor every other condition is compared against.

**Dataset:** `data/golden/lab01/eval.json` (≥60 cases, 5 classes, ≥12/class, ≥15%
`edge_case`/`ambiguous` tagged) + `data/golden/lab01/example_pool.json` (≥15 cases, disjoint
from eval, leakage-checked).

**Evaluation method:** closed-set label match (normalized: casefold, Turkish İ/ı-aware,
whitespace-trimmed) against gold label; priority field presence/validity; output-contract
compliance (no extra text outside the declared format — regex-checked per condition's
contract); per-constraint booleans aggregated into an "all constraints met" rate.

**Threats to validity:**
- *Single model.* All conclusions are specific to `openai/gpt-oss-20b` at the configured
  temperature/reasoning settings — explicitly stated in the report, never generalized.
  Lab 01 does not sweep models (that is Lab 05 of the *other* reference project's domain, out
  of scope here).
  explicitly stated in the report, never generalized.
- *Small classroom n.* With `classroom` profile (default repetitions=1, a stratified subset of
  cases), per-condition CIs will be wide. `comparison.md` auto-inserts the "differences may be
  noise" caution when CIs overlap substantially (Section 10 of the spec).
- *Fixture-mode results are not evidence of model behavior at all* — they test only that the
  pipeline computes the right thing when fed a known response, and are watermarked `SIMULATED`
  everywhere they appear.
- *Length-match control imperfection.* `B_len`'s neutral padding is topic-irrelevant boilerplate
  sized to match D's token count using the *local estimator*; because the estimator is a
  heuristic (see `docs/groq-capabilities.md` Section 6), the two conditions' *provider-reported*
  token counts may differ slightly. The report surfaces both the estimated and
  provider-reported token counts for this reason, rather than asserting exact equality.

Labs 02–08's full methodology sections are written as each lab is implemented (M3/M4), per the
spec's per-milestone process; their one-paragraph scenario/hypothesis previews already exist
in `docs/spec.md` Section 11.
