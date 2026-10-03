"""Is the weekday pattern in this series real?

The daily counts have weekday means from 81.0 to 104.0, a 23-trip spread that
looks like the obvious commuting pattern. A seasonal model would fit it.

The generator says otherwise: daily volume is `random.randint(70, 130)` with
no reference to the day of week. The weekday *shape* of trips within a day is
seasonal; the daily *total* is not.

So the spread is either noise or the generator is lying. A permutation test
settles it: shuffle the weekday labels many times and see how often chance
alone produces a spread this large. No distributional assumption needed.
"""

from __future__ import annotations

import datetime
import random
import statistics
from collections import defaultdict

from series import daily_counts


def weekday_spread(values: list[float], labels: list[int]) -> float:
    groups = defaultdict(list)
    for label, value in zip(labels, values):
        groups[label].append(value)
    means = [statistics.mean(v) for v in groups.values()]
    return max(means) - min(means)


def permutation_test(trials: int = 20_000, seed: int = 0) -> dict:
    dates, values = daily_counts()
    labels = [datetime.date.fromisoformat(d).weekday() for d in dates]
    observed = weekday_spread(values, labels)

    rng = random.Random(seed)
    shuffled = labels.copy()
    at_least_as_extreme = 0
    for _ in range(trials):
        rng.shuffle(shuffled)
        if weekday_spread(values, shuffled) >= observed:
            at_least_as_extreme += 1
    return {
        "observed_spread": observed,
        "p_value": (at_least_as_extreme + 1) / (trials + 1),
        "trials": trials,
    }


def main() -> None:
    dates, values = daily_counts()
    labels = [datetime.date.fromisoformat(d).weekday() for d in dates]
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    groups = defaultdict(list)
    for label, value in zip(labels, values):
        groups[label].append(value)

    print("mean daily trips by weekday")
    for i, name in enumerate(names):
        g = groups[i]
        print(f"  {name}  n={len(g):>2}  mean {statistics.mean(g):>6.1f}")

    result = permutation_test()
    print(f"\nobserved spread (max mean - min mean): {result['observed_spread']:.1f} trips")
    print(f"permutation p-value over {result['trials']} shuffles: {result['p_value']:.3f}")
    if result["p_value"] > 0.05:
        print("\nNot significant. The weekday pattern is sampling noise across ~8.6")
        print("observations per weekday -- which is what the generator says it is.")
        print("A seasonal model fitted to this is fitting nothing.")
    else:
        print("\nSignificant -- which would contradict the generator, and would mean")
        print("this file, not the generator, is the thing to re-read.")


if __name__ == "__main__":
    main()
