"""Four rate limiters with the same interface, and an injectable clock.

Every limiter takes `now` as an argument rather than calling time.time(), so
the tests are deterministic and a scenario spanning ten minutes runs in
microseconds. A limiter that sleeps is a limiter you cannot test.

Contract: `allow(now)` returns True if the request is admitted.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class FixedWindow:
    """Count requests per aligned window, reset at the boundary.

    The implementation everyone writes first, and the one this project exists
    to discredit. The counter resets on a clock boundary rather than relative
    to the requests, so a client that waits for the reset can spend a full
    allowance either side of it.
    """

    limit: int
    window: float
    count: int = 0
    window_start: float = field(default=0.0)
    name: str = "fixed window"

    def allow(self, now: float) -> bool:
        bucket = (now // self.window) * self.window
        if bucket != self.window_start:
            self.window_start = bucket
            self.count = 0
        if self.count < self.limit:
            self.count += 1
            return True
        return False


@dataclass
class SlidingLog:
    """Keep the timestamp of every admitted request; expire by age.

    Exact by construction: the invariant is literally the thing being
    promised, so there is no boundary to exploit. The cost is memory
    proportional to the limit -- every admitted request is retained for a
    full window.
    """

    limit: int
    window: float
    log: deque = field(default_factory=deque)
    name: str = "sliding log"

    def allow(self, now: float) -> bool:
        cutoff = now - self.window
        while self.log and self.log[0] <= cutoff:
            self.log.popleft()
        if len(self.log) < self.limit:
            self.log.append(now)
            return True
        return False


@dataclass
class SlidingCounter:
    """Two counters, weighted by how far into the current window we are.

    The standard production compromise: constant memory, no boundary doubling.
    It is still an approximation -- it assumes the previous window's requests
    were spread evenly, which a burst never is. How wrong it gets is measured
    rather than hand-waved.
    """

    limit: int
    window: float
    current: int = 0
    previous: int = 0
    window_start: float = 0.0
    name: str = "sliding counter"

    def allow(self, now: float) -> bool:
        bucket = (now // self.window) * self.window
        if bucket != self.window_start:
            # more than one window of silence wipes the history entirely
            self.previous = self.current if bucket - self.window_start == self.window else 0
            self.current = 0
            self.window_start = bucket
        elapsed = (now - self.window_start) / self.window
        estimate = self.previous * (1.0 - elapsed) + self.current
        if estimate < self.limit:
            self.current += 1
            return True
        return False


@dataclass
class TokenBucket:
    """Refill at limit/window tokens per second, up to `capacity`.

    Not a rate limiter for a fixed window -- a rate limiter with an explicit
    burst allowance. Setting capacity above the limit is a deliberate decision
    to permit bursts, which is different from a fixed window permitting them
    by accident.
    """

    limit: int
    window: float
    capacity: int | None = None
    tokens: float = field(default=None)
    last: float = 0.0
    name: str = "token bucket"

    def __post_init__(self) -> None:
        if self.capacity is None:
            self.capacity = self.limit
        if self.tokens is None:
            self.tokens = float(self.capacity)

    @property
    def rate(self) -> float:
        return self.limit / self.window

    def allow(self, now: float) -> bool:
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


def build(limit: int, window: float, start: float = 0.0) -> list:
    """One of each, all configured for the same nominal limit."""
    return [
        FixedWindow(limit, window, window_start=(start // window) * window),
        SlidingLog(limit, window),
        SlidingCounter(limit, window, window_start=(start // window) * window),
        TokenBucket(limit, window, last=start),
    ]
