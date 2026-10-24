from __future__ import annotations

import pytest

from lab_core.statistics import (
    bootstrap_ci,
    cis_overlap_substantially,
    mcnemar_exact,
    mean,
    paired_flips,
    wilson_ci,
)


def test_wilson_ci_point_estimate():
    ci = wilson_ci(successes=8, n=10)
    assert ci.point_estimate == pytest.approx(0.8)
    assert ci.low < 0.8 < ci.high
    assert 0.0 <= ci.low and ci.high <= 1.0


def test_wilson_ci_narrower_with_more_data_same_proportion():
    small = wilson_ci(successes=8, n=10)
    large = wilson_ci(successes=80, n=100)
    assert (large.high - large.low) < (small.high - small.low)


def test_wilson_ci_rejects_invalid_input():
    with pytest.raises(ValueError):
        wilson_ci(successes=11, n=10)
    with pytest.raises(ValueError):
        wilson_ci(successes=0, n=0)


def test_bootstrap_ci_deterministic_for_fixed_seed():
    values = [0.1, 0.5, 0.9, 0.3, 0.7, 0.2, 0.8]
    ci_a = bootstrap_ci(values, mean, resamples=200, seed=42)
    ci_b = bootstrap_ci(values, mean, resamples=200, seed=42)
    assert ci_a == ci_b


def test_bootstrap_ci_differs_for_different_seed():
    values = [0.1, 0.5, 0.9, 0.3, 0.7, 0.2, 0.8]
    ci_a = bootstrap_ci(values, mean, resamples=200, seed=1)
    ci_b = bootstrap_ci(values, mean, resamples=200, seed=2)
    assert (ci_a.low, ci_a.high) != (ci_b.low, ci_b.high)


def test_bootstrap_ci_contains_point_estimate_region():
    values = [1.0] * 20
    ci = bootstrap_ci(values, mean, resamples=100, seed=0)
    assert ci.point_estimate == 1.0
    assert ci.low == pytest.approx(1.0)
    assert ci.high == pytest.approx(1.0)


def test_paired_flips_requires_identical_case_sets():
    with pytest.raises(ValueError):
        paired_flips({"a": True}, {"b": True})


def test_paired_flips_counts_correctly():
    baseline = {"a": False, "b": True, "c": False, "d": True}
    treatment = {"a": True, "b": False, "c": False, "d": True}
    flips = paired_flips(baseline, treatment)
    assert flips.wrong_to_right == ["a"]
    assert flips.right_to_wrong == ["b"]
    assert flips.stayed_right == ["d"]
    assert flips.stayed_wrong == ["c"]
    assert flips.net_improvement == 0


def test_mcnemar_exact_symmetric_discordance_is_high_p():
    p = mcnemar_exact(b=5, c=5)
    assert p == pytest.approx(1.0)


def test_mcnemar_exact_no_discordance_is_one():
    assert mcnemar_exact(b=0, c=0) == 1.0


def test_mcnemar_exact_asymmetric_discordance_lowers_p():
    p_balanced = mcnemar_exact(b=10, c=10)
    p_skewed = mcnemar_exact(b=18, c=2)
    assert p_skewed < p_balanced


def test_cis_overlap_substantially_true_for_identical_intervals():
    from lab_core.statistics import ConfidenceInterval

    ci = ConfidenceInterval(point_estimate=0.5, low=0.3, high=0.7, n=10)
    assert cis_overlap_substantially(ci, ci) is True


def test_cis_overlap_substantially_false_for_disjoint_intervals():
    from lab_core.statistics import ConfidenceInterval

    ci_a = ConfidenceInterval(point_estimate=0.1, low=0.0, high=0.1, n=10)
    ci_b = ConfidenceInterval(point_estimate=0.9, low=0.8, high=1.0, n=10)
    assert cis_overlap_substantially(ci_a, ci_b) is False
