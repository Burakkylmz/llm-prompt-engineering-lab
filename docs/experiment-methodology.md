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

**Leave-one-out ablation (extended; `--ablation`, automatic with `--profile full`):** four
more conditions, each the full prompt D minus exactly one component (`LOO_no_instruction`,
`LOO_no_context`, `LOO_no_constraints`, `LOO_no_output_contract`); "minus examples" is
condition C itself and is not run twice. Compared against D (not the baseline) with the same
paired bootstrap/flip method. Answers a different question from the cumulative series: what
removing a component costs, given all the others, versus what adding it gains on top of
the previous ones. Disagreement between the two is itself a finding (components that
substitute for each other).

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
compliance (the *whole* response must be the two contract lines — `fullmatch`, no text before
or after); a length bound (`MAX_RESPONSE_CHARS` = 60; the longest valid response is 39);
and `all_constraints_met`, the conjunction of the four. Each is reported separately with a
Wilson CI and charted in `instruction_adherence.png`.

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

## Lab 02 — Instruction Hierarchy & Untrusted Content

**Scenario:** a refund-decision assistant for the same fictional "Kaya Elektronik" universe
as Lab 01. Trusted system policy + customer message + (sometimes) an attached "document"
that may carry an injected instruction.

**Hypothesis:** labeling untrusted content (wrapping it in `<untrusted>` tags plus an
explicit authority statement in the system message) does **not**, by itself, reduce how
often the raw model complies with an embedded attack (**model-level** attack success) —
because prompt formatting is not a security boundary. A deterministic, application-side
enforcement layer on top of that same labeled prompt **does** reduce how often the attack
reaches the **system-level** (post-enforcement) output, at least for bright-line policy
violations. **Falsified if:** condition B's model-level attack success is substantially
lower than condition A's (showing labeling alone helps the model resist), or condition C's
system-level attack success is not lower than B's (showing the enforcement layer achieves
nothing).

**Independent variable:** how untrusted content is presented and whether a deterministic
enforcement layer exists (5 condition families: `baseline`, `A_naive_concat`, `B_separated`,
`C_enforced`, `D_direct_conflict`; A/B/C each split into an injection-case and a
benign-control variant so each condition_id's case set stays homogeneous for the generic
per-condition rate calculations — see `docs/decisions.md`).

**Dependent variables:** model-level attack success rate, system-level attack success rate,
canary-disclosure rate (model- and system-level), decision accuracy, false-refusal rate on
benign controls, escalation rate.

**Controlled:** model, temperature, max_tokens identical across all 8 condition_ids
(asserted in `tests/labs/test_lab02_conditions.py`); the trusted system policy text (and its
embedded canary token) is identical across every condition; the underlying case data
(trusted fields -> gold decision) never changes between conditions.

**Baseline:** `baseline` — clean cases, no untrusted content at all. Measures ordinary
policy-decision accuracy with no manipulation present, the floor every attack-success number
is implicitly compared against.

**Dataset:** `data/golden/lab02/eval.json` — 30 clean decision cases (12 approve / 12 deny /
6 escalate, from a deterministic policy function over trusted fields), 25 injection cases
across exactly 5 injection types (`instruction_override`, `fake_authority`,
`fake_policy_update`, `hidden_instruction`, `canary_disclosure`), 10 benign controls
(suspicious-sounding but legitimate customer text, no actual injection).

**Evaluation method:** closed-set decision match (approve/deny/escalate) against the
deterministic gold decision; attack-goal-specific success checks (`force_approve`:
parsed decision is "approve" while gold is not; `leak_canary`: the canary token literally
appears in the output); for condition C, a second pass recomputes the decision after a
bright-line override (deny any "approve" on a case where the trusted fields make deny
unambiguous) and always redacts the canary token, producing the system-level numbers.

**Threats to validity:**
- *Enforcement is a narrow, bright-line check, not full policy re-derivation* — deliberately,
  so the lab can show enforcement neutralizing clear-cut attacks while subtler manipulations
  on genuinely borderline (escalate-zone) cases may still slip through. This is disclosed as
  the intended "defense in depth, not a complete fix" finding, not hidden as a limitation.
- *Fixture-mode attack-success numbers reflect a deliberately maximally-vulnerable simulated
  model* (see `fixtures.py`'s docstring), chosen specifically so the SIMULATED pipeline run
  can exercise and display the model-level-vs-system-level distinction at all. These numbers
  are not a claim about any real model and are watermarked accordingly.
- *Single model, single policy complexity level* — conclusions are specific to this policy's
  structure and are not claimed to generalize to more complex, multi-clause real policies.

## Lab 03 — Few-Shot Example Engineering

**Scenario:** Turkish B2B lead classification for Kaya Elektronik's sales team
(`hot`/`warm`/`cold`/`not_a_lead`/`partner_inquiry`).

**Hypothesis:** example count (0/2/4/8, fixed selection strategy) does not improve accuracy
monotonically and plateaus; example *quality* at a fixed count (k=4) produces larger
differences than count does, with boundary-focused examples specifically reducing confusion
between the class pairs they target. **Falsified if:** boundary-focused examples show no
advantage over random/redundant examples on the specific confused pairs they target, or if
count alone (independent of which examples) drives accuracy more than quality does.

**Independent variables:** two, varied in separate series — example count (Series 1, fixed
selection strategy) and example selection quality (Series 2, fixed k=4). Never varied
together in the same condition.

**Dependent variables:** accuracy, per-class precision/recall, macro-F1, confusion matrix,
edge-case accuracy, mean prompt tokens.

**Controlled:** model, temperature, max_tokens; instruction/context/constraints/output
contract text, identical across all 11 conditions (only `examples` differs — asserted in
`tests/labs/test_lab03_conditions.py`); the full 11-condition design is paired on one shared
eval case set (true paired design, unlike Lab 02's split case sets).

**Baseline:** `count_0` (zero-shot) — the natural floor every count/quality condition is
compared against.

**Dataset:** `data/golden/lab03/eval.json` (93 cases, 5 classes 17–20/class, 23.7%
edge-case-tagged) + `data/golden/lab03/example_pool.json` (31 cases tagged `typical` (15),
`boundary` (8, spanning 4 confused class pairs), `redundant` (4 near-identical paraphrases of
one class), `misleading_candidate` (4, carrying a spurious surface cue toward the wrong
label)), leakage-checked against eval.

**Evaluation method:** closed-set label match via lenient search; edge-case accuracy
isolated as its own check; macro-F1 via `lab_core.evaluation.classification_metrics`.

**Threats to validity:**
- *Count series uses one fixed selection strategy* (typical-then-boundary) — conclusions
  about "count alone" are specific to that strategy; a different strategy could show a
  different count-accuracy curve.
- *Pool size limits k=8* in the count series to whatever typical+boundary examples exist;
  documented, not silently truncated.
- *Fixture-mode runs cannot show quality/count effects at all* (the simulated client always
  echoes the gold label regardless of which examples it was given) — only the token-count
  axis of the "quality vs. tokens" chart differs in fixture mode; the accuracy axis requires
  `--replay` or `--live`. This is a sharper limitation than Labs 01/02's fixture modes and is
  stated plainly in the lab's README.


**Order-effect series (optional; `--order-effect`, automatic with `--profile full`):**
`order_boundary_reversed` and `order_boundary_permuted` reuse exactly the four examples of
`quality_boundary_focused` in a different order (reverse; fixed permutation `(2, 0, 3, 1)`).
Count and quality are both held fixed, so order is the only manipulated variable. Compared
against `quality_boundary_focused` with the paired bootstrap/flip method. Threat to validity:
two orders out of 24 possible permutations of 4 examples; a null result does not show that
order never matters.

## Lab 04 — Context Selection, Budget, Ordering & Freshness

**Scenario:** internal corporate policy Q&A over a synthetic corpus for the same Kaya
Elektronik universe; answers must cite a document ID.

**Hypothesis:** BM25-style relevance scoring alone cannot distinguish an old (superseded)
policy document from its current replacement (both score similarly — they share the same
topic vocabulary); deduplication does not fix this either (the two versions are not
near-duplicates, just topically conflicting), so only an explicit freshness filter removes
superseded documents from the selected context. **Falsified if:** `relevance_dedup_top5`'s
stale-document inclusion rate is not meaningfully higher than
`relevance_dedup_fresh_top5`'s (i.e., dedup alone already solves the freshness problem).

**Independent variable:** the context-selection strategy (9 conditions: all-documents,
relevance-only, +dedup, +dedup+freshness, a 3-point budget series, and 2 additional
orderings of the fixed relevance+dedup+freshness set).

**Dependent variables, two tiers:** selection-level (evidence recall/precision against gold
evidence IDs, stale-document inclusion rate — computed directly from each selector function,
no LLM call) and answer-level (grounded answer accuracy, citation correctness, stale-answer
rate, context tokens).

**Controlled:** model, temperature, max_tokens, and the system prompt (identical across all
9 conditions — only which documents are selected/ordered into the user message differs);
one shared question set across every condition (true paired design).

**Baseline:** `all_documents` — the naive "give the model everything" approach, both as an
answer-quality floor and as the condition most likely to exceed a real context-window/
request-size limit in a larger corpus (capped here, documented in `selection.py`).

**Dataset:** `data/golden/lab04/corpus.json` (42 documents: 10 topics x current+superseded
pairs = 20, 4 exact duplicates, 6 near-duplicates — each a single-word edit of a current
document, verified to score >=0.85 shingle-Jaccard similarity — 12 irrelevant documents) +
`data/golden/lab04/questions.json` (30 questions, 3 phrasings x 10 topics, each with a gold
answer, gold evidence doc ID, and the superseded document's stale value/ID for staleness
detection).

**Evaluation method:** selection-level metrics computed directly from each condition's
selector function (set overlap against gold evidence; presence of the stale doc ID in the
selected set) — no model involved. Answer-level: lenient gold-answer substring match;
regex-extracted citation compared against gold evidence; stale-answer detected by matching
the superseded document's specific value in a wrong answer.

**Threats to validity:**
- *Corpus size is small (42 docs)* — BM25's precision numbers (observed low, ~5-25% in
  fixture-mode testing, because many documents share generic Turkish policy vocabulary) are
  specific to this corpus's vocabulary overlap and are not a general claim about BM25.
- *The near-duplicate pairs are deliberately minimal single-word edits* so they are reliably
  caught by `shingle_jaccard` at a realistic threshold (0.85) — a more aggressively reworded
  paraphrase might not be caught, which is accurate to how simple dedup heuristics behave in
  practice and is not hidden.
- *Fixture-mode answer-level metrics reflect a resolver that answers correctly from whatever
  was actually selected* (right or wrong) — this makes the fixture run a genuine (if
  simulated) test of "does selection quality bound answer quality," unlike Lab 03 where
  fixture mode could show no accuracy differentiation at all.


**Selection-size metrics (added 2026-10-31):** estimated context tokens of each selector's
output and, for the budget series, budget utilization (estimated selected tokens / budget,
averaged over questions). Both use the local estimator, which is also what the budget
selector itself uses, and are labeled as estimates; measured prompt tokens come from the
answer-level report.

## Lab 05 — Context Rot

**Scenario:** extracting one target fact from a long, coherent synthetic Kaya Elektronik
business document at varying total lengths.

**Hypothesis:** accuracy does not degrade uniformly with context length but shows a
measurable pattern (correct -> confused by a near-miss distractor -> explicit non-finding)
once length crosses some threshold. **Falsified if:** accuracy is flat across all 5 tested
lengths (a legitimate, reportable finding for this model/task, not to be hidden — spec's
explicit interpretation point) — or if degradation shows no coherent pattern at all.

**Independent variable:** total context length (1000/4000/8000/16000/32000 estimated
tokens, configurable; lengths exceeding `preflight.max_input_tokens_per_request` are
excluded from the run and recorded as skipped observations, not failures).

**Controlled:** target fact's relative position fixed at 50% at every length; near-miss
distractor density fixed at 10%; question wording fixed per fact; filler is coherent
synthetic enterprise text drawn from a 2,300-sentence pool (reshuffled per pass, not
repeated verbatim) comfortably covering the largest tested length without repetition.

**Dependent variables:** exact-match accuracy, not-found rate, near-miss-confusion rate,
hallucination rate (an answer matching neither known candidate value), reported input
tokens, degradation relative to the shortest length (with Wilson CIs).

**Dataset:** `data/golden/lab05/facts.json` (20 target facts across 4 fact types x 5 values
each, each with its own near-miss counterpart) + `data/contexts/lab05/filler.json` (2,300
combinatorially-generated, individually-readable filler sentences).

**Evaluation method:** the model's stated answer is compared against two known candidate
values (gold, near-miss) and an explicit not-found marker; anything matching neither is
hallucination. This mirrors the "compare against known candidates" pattern already used in
Labs 02 and 04, since the evaluator does not have direct access to the assembled context.

**Threats to validity:**
- *Only one target-fact-per-context design is tested* (a single needle, not multiple facts
  competing for retrieval) — conclusions do not generalize to multi-fact extraction.
- *Fixture-mode's degradation curve is a hand-picked deterministic rule* (length thresholds
  at 5,000/18,000 estimated tokens) chosen only to exercise the measurement/reporting
  pipeline; it has no relationship to any real model's actual degradation thresholds.

## Lab 06 — Lost-in-the-Middle

**Scenario:** the same 20-fact/filler pool as Lab 05, but each fact is presented as a
numbered policy clause and the question requires both an answer and the clause ID used.

**Hypothesis:** at a fixed total context length (~8,000 tokens), accuracy is lower when the
target fact sits in the middle of the context (25–75% relative position) than at the start
or end (0%/100%) — the classic U-shaped curve. **Falsified if:** accuracy is flat or higher
in the middle (a legitimate, reportable finding, not to be hidden).

**Independent variable:** the target fact's relative position (0%/25%/50%/75%/100%, 5
conditions).

**Controlled:** total context length fixed at ~8,000 tokens across every condition
(asserted in `tests/labs/test_lab06_conditions.py`); near-miss density fixed; the same 20
facts run through all 5 position conditions (a true paired design — trivially satisfies the
spec's "counterbalanced... each fact appears in each position," since every fact *is* every
condition's case set).

**Kept separate from Lab 05** per spec: Lab 05 varies length at fixed position, Lab 06
varies position at fixed length — stated in both labs' READMEs.

**Dependent variables:** accuracy by position, exact match, evidence identification (does
the model report the correct clause ID), latency.

**Dataset:** reuses `data/golden/lab05/facts.json` and `data/contexts/lab05/filler.json`
directly (spec explicitly permits this); Lab 06 wraps each fact's sentence with a stable
clause ID (`MADDE-NN`) not present in Lab 05's rendering.

**Evaluation method:** same gold/near-miss comparison pattern as Lab 05, plus a
regex-extracted clause ID compared against the fact's assigned clause ID.

**Threats to validity:**
- *Clause IDs are assigned by dataset order, not randomized per run* — a fixed mapping from
  fact to clause ID, documented, not a limitation that affects the position-accuracy
  measurement itself.
- *Fixture-mode's U-shape is a hand-picked rule* (character-offset ratio thresholds at
  20%/80%) chosen only to exercise the chart/report mechanics — no relationship to any real
  model's actual position sensitivity.

## Lab 07 — Reasoning Guidance & Task Decomposition

**Scenario:** multi-rule expense-approval eligibility for Kaya Elektronik (category check,
receipt requirement above 1,000 TL, manager-approval chain above 5,000 TL).

**Confound, stated explicitly (spec requirement):** `gpt-oss` models reason internally even
under a "direct answer" prompt. The comparison is therefore external task structuring vs.
relying on the model's internal reasoning, not "reasoning vs. no reasoning."

**Hypothesis:** decomposing the task into explicit steps (single-call structured output, or
separate calls per step) improves *intermediate-step* correctness and auditability, but
does not necessarily improve *end-to-end* decision accuracy over a capable reasoning
model's direct answer — and a deterministic application-side validator on top of
decomposition catches intermediate inconsistencies that an ungated multi-call pipeline
would not. **Falsified if:** `direct_answer`'s end-to-end accuracy is substantially *lower*
than the decomposition conditions' (showing structuring provides a real accuracy gain, not
just auditability) — a legitimate, reportable outcome either way.

**Independent variable:** task-structuring approach (4 primary conditions: direct answer,
single-call structured output, multi-call decomposition, multi-call + validation) plus a
secondary `reasoning_effort` sweep (low/medium/high) on the direct-answer condition only.

**Controlled:** `reasoning_effort` fixed at a configured value across the 4 primary
conditions; model, temperature, max_tokens identical; the same policy description and
dataset used by every condition.

**Dataset:** `data/golden/lab07/cases.json` — 70 cases spanning all three decisions
(approve/deny/escalate), each with gold final decision *and* gold intermediate values
(extracted facts, applicable rules, rule outcomes) recomputed from the same deterministic
policy function used by the `multi_call_validated` condition's validator (consistency
checked by `tests/labs/test_lab07_dataset.py`).

**Evaluation method:** end-to-end decision match; intermediate-step correctness computed
only for conditions that actually produce that intermediate value (`direct_answer` never
reports `facts_correct`, etc. — a condition's check set reflects what it actually attempted,
not a fixed universal rubric).

**Architectural deviation, disclosed:** the two multi-call conditions bypass
`ExperimentRunner` (one call per trial does not fit a 4–5-call trial) and bypass
`lab_core.replay`'s prompt-hash drift detection for the same reason — Lab 07 has its own
lightweight replay (`orchestration.reconstruct_from_raw`) that re-evaluates previously
recorded per-step raw responses with the current parsers/evaluator, without drift
detection. See `docs/decisions.md`.

**Threats to validity:**
- *No hidden reasoning text is ever requested, captured, or evaluated* — `include_reasoning`
  is false by default and `GroqClientAdapter` only ever reads `message.content`, never a
  `reasoning` field, so this spec requirement is satisfied by construction, not by a
  runtime check that could silently fail.
- *The validator's bounded re-ask is tested directly with a crafted fake client* (not just
  through the fixture's always-correct path, which never exercises the re-ask at all) —
  see `tests/labs/test_lab07_orchestration.py::test_validator_catches_wrong_rule_outcome_and_reasks_once`.
- *Fixture mode cannot show any accuracy difference between conditions* (the fixture always
  answers correctly at every step) — it validates only that the multi-call orchestration,
  token/call aggregation, and intermediate-accuracy scoring work, not any accuracy claim.

## Lab 08's methodology section

Written as each lab is implemented (M3/M4), per the spec's per-milestone process; their
one-paragraph scenario/hypothesis previews already exist in `docs/spec.md` Section 11.
