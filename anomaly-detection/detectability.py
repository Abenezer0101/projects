"""What a monitor cannot see, whatever algorithm it runs.

The Poisson detector finds every injected spike and only 3 of 12 dropouts.
That is not a tuning failure. For event counts with rate mu, a complete outage
sits exactly

    mu / sqrt(mu) = sqrt(mu)

standard deviations below the mean. So a total outage is visible at a k-sigma
threshold only when

    mu >= k^2

At k = 3 that means 9 events per interval. In this series only 08:00 clears
it, at 9.57 trips an hour -- 1 of 24 hours. Twenty-three hours a day, an
hour-long total outage is mathematically inside the noise.

The fix is not a better detector. It is a longer interval: the DAILY rate is
about 97 trips, so a full day's outage is sqrt(97) = 9.8 sigma, and even a
single missing hour is easier to see in a daily total than in its own bucket.
Choosing the aggregation window is the actual design decision, and no amount
of algorithm selection substitutes for it.
"""

from __future__ import annotations

import math
import statistics

from series import hourly_counts


def sigmas_for_outage(rate: float) -> float:
    """How many sigma below the mean a complete outage sits."""
    return math.sqrt(rate) if rate > 0 else 0.0


def min_rate_for_threshold(threshold: float) -> float:
    return threshold * threshold


def per_hour_rates() -> dict[int, float]:
    stamps, values = hourly_counts()
    by_hour: dict[int, list[float]] = {}
    for stamp, value in zip(stamps, values):
        by_hour.setdefault(stamp.hour, []).append(value)
    return {hour: statistics.mean(vs) for hour, vs in sorted(by_hour.items())}


def daily_rate() -> float:
    stamps, values = hourly_counts()
    by_day: dict[str, float] = {}
    for stamp, value in zip(stamps, values):
        key = stamp.date().isoformat()
        by_day[key] = by_day.get(key, 0.0) + value
    # drop the first and last day, which are partial in this file
    days = sorted(by_day)[1:-1]
    return statistics.mean(by_day[d] for d in days)


def main() -> None:
    threshold = 3.0
    needed = min_rate_for_threshold(threshold)
    print(f"a complete outage sits sqrt(mu) sigma below a Poisson mean of mu,")
    print(f"so it reaches {threshold:g} sigma only when mu >= {needed:g} "
          f"events per interval\n")

    rates = per_hour_rates()
    visible = [h for h, r in rates.items() if sigmas_for_outage(r) >= threshold]
    print(f"  {'hour':>5} {'rate':>8} {'sigma':>7}   outage visible?")
    for hour, rate in rates.items():
        s = sigmas_for_outage(rate)
        mark = "YES" if s >= threshold else ""
        print(f"  {hour:>5} {rate:>8.2f} {s:>7.2f}   {mark}")
    print(f"\n{len(visible)} of 24 hours clear it: {visible}")

    d = daily_rate()
    print(f"\naggregated to a whole day the rate is {d:.1f} trips, so a full")
    print(f"day of outage is sqrt({d:.1f}) = {sigmas_for_outage(d):.1f} sigma -- "
          f"trivially visible.")
    print("The aggregation window is the design decision. Picking a cleverer")
    print("detector at the wrong window cannot recover information that is")
    print("not in the bucket.")


if __name__ == "__main__":
    main()
