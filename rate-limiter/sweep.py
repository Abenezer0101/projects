"""Search for each limiter's worst case instead of assuming the textbook one.

The boundary attack is the known exploit against a fixed window. Rather than
trust that it is also the worst case, this sweeps the burst's offset across a
whole window and reports the largest violation found for each limiter.
"""

from __future__ import annotations

from audit import replay, worst_window
from limiter import build

LIMIT = 100
WINDOW = 60.0


def burst_at(offset: float, n: int = 400, spacing: float = 1e-4) -> list[float]:
    """A tight burst of `n` requests starting `offset` seconds into a window."""
    base = 600.0 + offset
    return [base + i * spacing for i in range(n)]


def two_bursts(offset: float, n: int = 200, spacing: float = 1e-4) -> list[float]:
    """The classic: half the burst before a boundary, half after."""
    boundary = 600.0
    first = [boundary - offset + i * spacing for i in range(n)]
    second = [boundary + i * spacing for i in range(n)]
    return sorted(first + second)


def sweep() -> dict[str, tuple[int, float]]:
    worst: dict[str, tuple[int, float]] = {}
    for offset in [i * WINDOW / 120 for i in range(1, 120)]:
        for arrivals in (burst_at(offset), two_bursts(offset)):
            for lim in build(LIMIT, WINDOW, start=arrivals[0]):
                n, _ = worst_window(replay(lim, arrivals), WINDOW)
                if n > worst.get(lim.name, (0, 0.0))[0]:
                    worst[lim.name] = (n, offset)
    return worst


def sustained(rate_multiple: float = 3.0, minutes: int = 10) -> dict[str, float]:
    """Hammer at 3x the limit for ten minutes; measure the long-run rate let through."""
    total = int(LIMIT * rate_multiple * minutes)
    span = WINDOW * minutes
    arrivals = [i * span / total for i in range(total)]
    out = {}
    for lim in build(LIMIT, WINDOW, start=0.0):
        got = replay(lim, arrivals)
        out[lim.name] = len(got) / minutes
    return out


def main() -> None:
    print(f"limit {LIMIT} per {WINDOW:g}s\n")
    print("worst case found over 119 burst offsets x 2 attack shapes:")
    print(f"  {'limiter':17} {'worst window':>13} {'ratio':>7}")
    for name, (n, offset) in sorted(sweep().items(), key=lambda kv: -kv[1][0]):
        print(f"  {name:17} {n:>13} {n / LIMIT:>6.2f}x")

    print(f"\nsustained load at 3x the limit for 10 minutes "
          f"(requests admitted per minute, target {LIMIT}):")
    for name, rate in sorted(sustained().items(), key=lambda kv: -kv[1]):
        print(f"  {name:17} {rate:>7.1f}")


if __name__ == "__main__":
    main()
