"""Confidence intervals and paired-comparison statistics (spec Section 10).

All randomized procedures (bootstrap) are seeded for determinism. Nothing here claims
statistical significance on its own — `mcnemar_exact` is explicitly labeled exploratory by
callers (reporting.py), never surfaced as a significance claim in a default classroom run.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceInterval:
    point_estimate: float
    low: float
    high: float
    n: int


def wilson_ci(successes: int, n: int, z: float = 1.96) -> ConfidenceInterval:
    """95%-by-default Wilson score interval for a proportion. Preferred over the normal
    (Wald) interval because it stays inside [0, 1] and behaves sensibly for small n and
    extreme proportions — exactly the classroom-run regime this project targets."""
    if n <= 0:
        raise ValueError("n must be > 0")
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")

    p_hat = successes / n
    denom = 1 + (z**2) / n
    center = p_hat + (z**2) / (2 * n)
    margin = z * math.sqrt((p_hat * (1 - p_hat) / n) + (z**2) / (4 * n**2))
    low = (center - margin) / denom
    high = (center + margin) / denom
    # Clamp to [0, 1] AND to always contain p_hat: floating-point rounding can otherwise put
    # `high` a hair below (or `low` a hair above) the point estimate at the extremes (e.g.
    # successes == n), which would silently violate "the interval contains the estimate" for
    # any downstream consumer (e.g. a chart computing a yerr from high - point_estimate).
    low = min(max(0.0, low), p_hat)
    high = max(min(1.0, high), p_hat)
    return ConfidenceInterval(point_estimate=p_hat, low=low, high=high, n=n)


def bootstrap_ci(
    values: Sequence[float],
    statistic_fn: Callable[[Sequence[float]], float],
    resamples: int = 1000,
    seed: int = 0,
    confidence: float = 0.95,
) -> ConfidenceInterval:
    """Seeded percentile bootstrap CI for an arbitrary statistic (e.g. macro-F1, a mean
    difference between paired conditions). Deterministic for a fixed seed/resamples/values —
    tested explicitly so classroom runs are reproducible."""
    if not values:
        raise ValueError("values must be non-empty")
    if resamples < 1:
        raise ValueError("resamples must be >= 1")

    rng = random.Random(seed)
    n = len(values)
    point_estimate = statistic_fn(values)

    resample_stats = []
    for _ in range(resamples):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        resample_stats.append(statistic_fn(resample))

    resample_stats.sort()
    alpha = 1 - confidence
    low_idx = max(0, int((alpha / 2) * resamples))
    high_idx = min(resamples - 1, int((1 - alpha / 2) * resamples) - 1)
    return ConfidenceInterval(
        point_estimate=point_estimate,
        low=resample_stats[low_idx],
        high=resample_stats[high_idx],
        n=n,
    )


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


@dataclass(frozen=True)
class PairedFlips:
    """Per-case outcome changes between a baseline condition and a treatment condition,
    matched by case_id. Both conditions must have evaluated the identical case set
    (spec Section 8's paired-design requirement) — mismatched case sets raise, rather than
    silently comparing a subset."""

    wrong_to_right: list[str]
    right_to_wrong: list[str]
    stayed_right: list[str]
    stayed_wrong: list[str]

    @property
    def net_improvement(self) -> int:
        return len(self.wrong_to_right) - len(self.right_to_wrong)


def paired_flips(
    baseline_correct: dict[str, bool], treatment_correct: dict[str, bool]
) -> PairedFlips:
    if set(baseline_correct.keys()) != set(treatment_correct.keys()):
        raise ValueError(
            "paired_flips requires baseline and treatment to cover the identical case_id set "
            f"(baseline has {len(baseline_correct)}, treatment has {len(treatment_correct)})"
        )

    wrong_to_right, right_to_wrong, stayed_right, stayed_wrong = [], [], [], []
    for case_id, was_correct in baseline_correct.items():
        is_correct = treatment_correct[case_id]
        if not was_correct and is_correct:
            wrong_to_right.append(case_id)
        elif was_correct and not is_correct:
            right_to_wrong.append(case_id)
        elif was_correct and is_correct:
            stayed_right.append(case_id)
        else:
            stayed_wrong.append(case_id)

    return PairedFlips(
        wrong_to_right=wrong_to_right,
        right_to_wrong=right_to_wrong,
        stayed_right=stayed_right,
        stayed_wrong=stayed_wrong,
    )


def mcnemar_exact(b: int, c: int) -> float:
    """Exact McNemar test p-value via the binomial distribution, for the discordant-pair
    counts b (wrong->right) and c (right->wrong). EXPLORATORY ONLY — callers must label it as
    such; this project never claims significance from it in a default classroom-sized run
    (spec Section 10)."""
    if b < 0 or c < 0:
        raise ValueError("b and c must be >= 0")
    n = b + c
    if n == 0:
        return 1.0

    k = min(b, c)

    def binom_pmf(x: int, trials: int, p: float = 0.5) -> float:
        return math.comb(trials, x) * (p**x) * ((1 - p) ** (trials - x))

    # Two-sided exact test: sum the probability of outcomes at least as extreme as k.
    p_value = sum(binom_pmf(x, n) for x in range(0, k + 1))
    p_value += sum(binom_pmf(x, n) for x in range(n - k, n + 1))
    # Avoid double-counting the symmetric middle when n is even and k == n - k.
    if k == n - k:
        p_value -= binom_pmf(k, n)
    return min(1.0, p_value)


def cis_overlap_substantially(ci_a: ConfidenceInterval, ci_b: ConfidenceInterval) -> bool:
    """Heuristic used by reporting.py to decide whether to insert the 'may be noise' caution:
    true when the intervals overlap by more than half of the narrower interval's width."""
    overlap_low = max(ci_a.low, ci_b.low)
    overlap_high = min(ci_a.high, ci_b.high)
    overlap = max(0.0, overlap_high - overlap_low)
    narrower_width = min(ci_a.high - ci_a.low, ci_b.high - ci_b.low)
    if narrower_width <= 0:
        return overlap > 0
    return overlap / narrower_width > 0.5
