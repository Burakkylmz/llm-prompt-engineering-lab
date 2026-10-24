"""Client-side rate limiting and retry backoff.

Two independent, composable pieces:
  - `compute_backoff_delay_seconds`: a policy-free exponential-backoff-with-jitter helper
    (mirrors the reference repo's design — not auto-wired into any client, so retry policy
    stays an explicit, testable decision made by the caller).
  - `RateLimiter`: a token-bucket-style limiter honoring configured RPM/TPM, with an
    injectable clock and sleep function so tests never actually sleep.
"""

from __future__ import annotations

import random
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass


def compute_backoff_delay_seconds(
    attempt: int,
    base_delay_seconds: float,
    max_delay_seconds: float,
    jitter: bool,
    retry_after_seconds: float | None = None,
) -> float:
    """Delay before retry attempt `attempt` (1-indexed).

    If the provider sent a `retry-after` header, honor it directly (it reflects the
    provider's own rate-limit-reset knowledge, which is more accurate than a local guess).
    Otherwise use exponential backoff: base * 2^(attempt-1), capped at max_delay_seconds,
    with optional full jitter (uniform in [0, capped_delay]).
    """
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if retry_after_seconds is not None:
        return max(0.0, retry_after_seconds)

    exponential_delay = base_delay_seconds * (2 ** (attempt - 1))
    capped_delay = min(exponential_delay, max_delay_seconds)
    if jitter:
        return random.uniform(0, capped_delay)
    return capped_delay


@dataclass
class _Usage:
    timestamp: float
    tokens: int


class RateLimiter:
    """Sliding-60-second-window limiter on requests/minute and tokens/minute.

    `clock` and `sleep` are injectable (default `time.monotonic` / `time.sleep`) so unit
    tests can run instantly and deterministically.
    """

    def __init__(
        self,
        requests_per_minute: float,
        tokens_per_minute: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if requests_per_minute <= 0 or tokens_per_minute <= 0:
            raise ValueError("requests_per_minute and tokens_per_minute must be > 0")
        self._rpm = requests_per_minute
        self._tpm = tokens_per_minute
        self._clock = clock
        self._sleep = sleep
        self._history: deque[_Usage] = deque()

    def _prune(self, now: float) -> None:
        window_start = now - 60.0
        while self._history and self._history[0].timestamp < window_start:
            self._history.popleft()

    def acquire(self, estimated_tokens: int) -> float:
        """Block (via injected sleep) until a request of this estimated size is permitted.

        Returns the number of seconds actually waited (0.0 if no wait was needed).
        """
        waited = 0.0
        while True:
            now = self._clock()
            self._prune(now)
            request_count = len(self._history)
            token_count = sum(u.tokens for u in self._history)

            if request_count < self._rpm and token_count + estimated_tokens <= self._tpm:
                self._history.append(_Usage(timestamp=now, tokens=estimated_tokens))
                return waited

            oldest = self._history[0]
            delay = max(0.0, (oldest.timestamp + 60.0) - now)
            delay = max(delay, 0.05)
            self._sleep(delay)
            waited += delay
