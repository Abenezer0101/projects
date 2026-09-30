"""Adjudicator: given the times a limiter admitted requests, what is the most
it ever let through in ANY window of length W?

This is the only number that matters. A limiter configured for "100 per
minute" is wrong if some 60-second stretch anywhere in the trace contains 101.
Checking aligned windows -- the mistake the fixed-window limiter itself makes
-- would let it mark its own homework.
"""

from __future__ import annotations


def worst_window(admitted: list[float], window: float) -> tuple[int, float]:
    """Max admitted in any window of length `window`, and where it starts.

    Each admitted request starts a candidate window, which is sufficient: the
    densest half-open window [t, t+W) can always be slid left until its left
    edge sits on an admitted request without losing any.
    """
    if not admitted:
        return 0, 0.0
    times = sorted(admitted)
    best, at, j = 0, times[0], 0
    for i, start in enumerate(times):
        while j < len(times) and times[j] < start + window:
            j += 1
        if j - i > best:
            best, at = j - i, start
    return best, at


def replay(limiter, arrivals: list[float]) -> list[float]:
    return [t for t in arrivals if limiter.allow(t)]
