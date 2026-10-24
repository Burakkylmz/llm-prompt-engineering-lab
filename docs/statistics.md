# Statistics: Confidence Intervals, Bootstrap, Flips, and Why Small Runs Are Noisy

Implemented in `src/lab_core/statistics.py`. This document explains what each number in a
`comparison.md` report means and why the `classroom` profile's results should be read
cautiously.

## Why this matters

The `classroom` profile (default `max_cases=10`, `repetitions=1`) exists so a training
session can run every lab in minutes without hitting rate limits. But a 10-case, 1-repetition
sample is small enough that normal sampling noise can easily look like a real effect. This
project's statistics layer exists specifically to stop that misreading — every report states
its uncertainty, and the report itself inserts a caution when that uncertainty is large
relative to the effect being compared.

## Wilson confidence intervals (proportions)

Accuracy, instruction-adherence rate, parse-success rate, attack-success rate, and every
other proportion-shaped metric in this project are reported as a point estimate **plus a 95%
Wilson score interval**, not a plain `successes/n` percentage.

Why Wilson and not the textbook normal-approximation ("Wald") interval: Wald intervals can
extend below 0% or above 100% and behave badly exactly in the regime this project lives in —
small `n` (10–60 cases) and proportions near 0 or 1 (e.g. a 9/10 or 10/10 accuracy run). Wilson
intervals stay inside `[0, 1]` and have better coverage at these sample sizes. With `n=10` and
8 successes, for example, the point estimate is 80% but the 95% Wilson interval is roughly
`[49%, 94%]` — wide enough that "80% vs. 70%" between two conditions on 10 cases each tells
you almost nothing on its own.

## Bootstrap confidence intervals (macro-F1 and other composite statistics)

Macro-F1 and any other statistic that isn't a simple proportion get a **seeded percentile
bootstrap** interval instead (`bootstrap_ci`, default 1000 resamples). The seed makes every
run of the same analysis on the same data reproduce the identical interval — this is tested
directly (`tests/core/test_statistics.py::test_bootstrap_ci_deterministic_for_fixed_seed`) so
a participant who reruns `lab-runner report` gets the same numbers, not a slightly different
interval each time.

## Per-case flips (paired comparisons)

Because every lab uses a **paired design** (every condition runs on the identical case set),
the report doesn't stop at "condition B is 5 points more accurate than baseline" — it also
lists exactly which `case_id`s flipped `wrong -> right` and which flipped `right -> wrong`
(`paired_flips`, surfaced in `comparison.md` under "Per-case flips vs. baseline"). A condition
that improves 3 cases while breaking 3 different cases nets to "no change" in the headline
accuracy number but is a very different (and more interesting) result than a condition that
simply gets 3 more cases right with no regressions. Always read the flips, not just the net.

## McNemar's exact test (exploratory only)

`mcnemar_exact(b, c)` computes an exact two-sided p-value from the discordant-pair counts
(`b` = wrong->right, `c` = right->wrong). **This project never surfaces this as a
significance claim in a default classroom-sized run.** It exists for instructors who want to
discuss statistical testing explicitly, and anywhere it is shown it must be labeled
"exploratory." With `classroom`-sized `n`, the test has very low power — a real effect can
easily produce a non-significant p-value, and a non-significant p-value is not evidence of
"no difference."

## The automatic noise caution

`render_comparison_markdown` compares each treatment condition's accuracy CI against the
baseline's CI (`cis_overlap_substantially`: true when the overlap exceeds half of the
narrower interval's width) and, when true, appends:

> **Caution:** the confidence interval for `<conditions>` overlaps substantially with the
> baseline's. Differences within this run may be noise.

This is not a p-value and does not replace proper inference — it is a cheap, always-on
tripwire against the single most common misreading of a small classroom run: treating two
overlapping, noisy intervals as if one condition had "won."

## Repetitions and consistency

When `repetitions > 1` (the `full` profile default is 3), the API is **not** assumed to
return identical output on every call for the same input — this is explicitly not assumed
anywhere in this project, even at `temperature=0.0`. A future addition (tracked in
`docs/tasks.md` for later labs) is a per-case consistency metric (fraction of repetitions
agreeing). For Lab 01 at M2, each condition/case pair's repetitions are all persisted as
separate observations; `summarize_condition` currently aggregates across all repetitions
together rather than reporting per-repetition consistency — this is a known scope boundary at
the M2 checkpoint, not a hidden limitation (see the checkpoint report's open questions).

## Missing values

Any metric that cannot be computed — no verified pricing, no reported token usage, a
condition with zero usable observations — is reported as `null` with an explicit reason
string, never as `0`. A `0` would claim "the API reported zero tokens" or "the cost is zero,"
which is a different and false claim from "this was not measured." See
`lab_core.metrics.estimate_cost` for the canonical example.
