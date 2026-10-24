from __future__ import annotations

import pytest

from lab_core.rate_limiter import RateLimiter, compute_backoff_delay_seconds


def test_backoff_grows_exponentially_without_jitter():
    d1 = compute_backoff_delay_seconds(
        1, base_delay_seconds=1.0, max_delay_seconds=100.0, jitter=False
    )
    d2 = compute_backoff_delay_seconds(
        2, base_delay_seconds=1.0, max_delay_seconds=100.0, jitter=False
    )
    d3 = compute_backoff_delay_seconds(
        3, base_delay_seconds=1.0, max_delay_seconds=100.0, jitter=False
    )
    assert (d1, d2, d3) == (1.0, 2.0, 4.0)


def test_backoff_capped_at_max():
    d = compute_backoff_delay_seconds(
        10, base_delay_seconds=1.0, max_delay_seconds=5.0, jitter=False
    )
    assert d == 5.0


def test_backoff_honors_retry_after_header():
    d = compute_backoff_delay_seconds(
        1, base_delay_seconds=1.0, max_delay_seconds=100.0, jitter=False, retry_after_seconds=17.0
    )
    assert d == 17.0


def test_backoff_jitter_within_bounds():
    for _ in range(50):
        d = compute_backoff_delay_seconds(
            3, base_delay_seconds=1.0, max_delay_seconds=100.0, jitter=True
        )
        assert 0.0 <= d <= 4.0


def test_backoff_rejects_invalid_attempt():
    with pytest.raises(ValueError):
        compute_backoff_delay_seconds(
            0, base_delay_seconds=1.0, max_delay_seconds=10.0, jitter=False
        )


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_rate_limiter_allows_up_to_rpm_without_sleeping():
    clock = _FakeClock()
    sleeps: list[float] = []
    limiter = RateLimiter(
        requests_per_minute=3, tokens_per_minute=10_000, clock=clock, sleep=sleeps.append
    )
    for _ in range(3):
        waited = limiter.acquire(estimated_tokens=10)
        assert waited == 0.0
    assert sleeps == []


def test_rate_limiter_sleeps_when_rpm_exceeded():
    clock = _FakeClock()

    def fake_sleep(seconds: float) -> None:
        clock.now += seconds

    limiter = RateLimiter(
        requests_per_minute=2, tokens_per_minute=10_000, clock=clock, sleep=fake_sleep
    )
    limiter.acquire(10)
    limiter.acquire(10)
    waited = limiter.acquire(10)  # 3rd request must wait for the window to free up
    assert waited > 0.0


def test_rate_limiter_sleeps_when_tpm_exceeded():
    clock = _FakeClock()

    def fake_sleep(seconds: float) -> None:
        clock.now += seconds

    limiter = RateLimiter(
        requests_per_minute=100, tokens_per_minute=100, clock=clock, sleep=fake_sleep
    )
    limiter.acquire(60)
    waited = limiter.acquire(60)  # would exceed 100 tokens/min
    assert waited > 0.0


def test_rate_limiter_rejects_non_positive_limits():
    with pytest.raises(ValueError):
        RateLimiter(requests_per_minute=0, tokens_per_minute=10)
