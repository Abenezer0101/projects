"""What repeated looks at a running A/B test do to the false-positive rate.

Every experiment simulated here is an A/A test: both arms are drawn from the
same distribution, so there is no effect to find and every "significant"
result is a false positive. The nominal rate is 5%.

Stopping the moment you see p < 0.05 is not a 5% test. It is a test that gets
as many chances as you give it, and the measured rate below is what that costs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from stats import BinomialSampler, two_sided_p, z_score

BASE_RATE = 0.10
PER_DAY = 1000      # users per arm per day
DAYS = 14
ALPHA = 0.05


@dataclass
class Outcome:
    significant: bool
    stopped_on: int          # day the decision was made
    observed_lift: float     # relative lift at the stopping point


def run_experiment(rng: random.Random, sampler: BinomialSampler, *,
                   looks: list[int], alpha: float = ALPHA,
                   threshold_z: float | None = None) -> Outcome:
    """One A/A experiment, inspected on the given days, stopping at the first
    look that clears the bar."""
    x_a = x_b = 0
    n = 0
    for day in range(1, DAYS + 1):
        x_a += sampler.draw(rng)
        x_b += sampler.draw(rng)
        n += PER_DAY
        if day not in looks:
            continue
        z = z_score(x_a, n, x_b, n)
        hit = abs(z) >= threshold_z if threshold_z is not None else two_sided_p(z) < alpha
        if hit:
            rate_a, rate_b = x_a / n, x_b / n
            lift = (rate_a - rate_b) / rate_b if rate_b else 0.0
            return Outcome(True, day, lift)
    rate_a, rate_b = x_a / n, x_b / n
    return Outcome(False, DAYS, (rate_a - rate_b) / rate_b if rate_b else 0.0)


def false_positive_rate(looks: list[int], trials: int = 20_000, seed: int = 0,
                        threshold_z: float | None = None) -> tuple[float, list[Outcome]]:
    rng = random.Random(seed)
    sampler = BinomialSampler(PER_DAY, BASE_RATE)
    hits = []
    for _ in range(trials):
        out = run_experiment(rng, sampler, looks=looks, threshold_z=threshold_z)
        if out.significant:
            hits.append(out)
    return len(hits) / trials, hits


POLICIES = {
    "one look, at the end": [DAYS],
    "look on day 7 and day 14": [7, DAYS],
    "look every other day": list(range(2, DAYS + 1, 2)),
    "look every day": list(range(1, DAYS + 1)),
}


def main() -> None:
    print(f"A/A tests: both arms at {BASE_RATE:.0%}, {PER_DAY} users/arm/day, "
          f"{DAYS} days, alpha={ALPHA}")
    print("every 'significant' result below is a false positive by construction\n")
    print(f"{'stopping rule':28} {'looks':>6} {'false positives':>16}")
    print("-" * 54)
    for name, looks in POLICIES.items():
        rate, hits = false_positive_rate(looks)
        print(f"{name:28} {len(looks):>6} {rate:>15.1%}")

    rate, hits = false_positive_rate(list(range(1, DAYS + 1)))
    if hits:
        mean_lift = sum(abs(h.observed_lift) for h in hits) / len(hits)
        mean_day = sum(h.stopped_on for h in hits) / len(hits)
        print(f"\namong the {len(hits)} false positives from daily looks:")
        print(f"  mean |observed lift| {mean_lift:>6.1%}  (the true lift is 0)")
        print(f"  mean stopping day    {mean_day:>6.1f} of {DAYS}")
        print("  stopping early is what makes the number big: you stop exactly")
        print("  when noise is at its most flattering, and report that as the effect")


if __name__ == "__main__":
    main()
