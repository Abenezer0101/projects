"""The irreducible error, in closed form -- the thing real data never gives you.

The generator for this series is one line:

    for _ in range(random.randint(70, 130)):

So daily volume is i.i.d. DiscreteUniform{70..130}. Nothing depends on the
previous day, the weekday, or the date. That pins three numbers exactly.

Let N = 61 (the number of possible values) with mean 100.

  Best possible forecast is the constant 100, and its expected absolute error
  is  E|X - 100| = (1/61) * 2 * sum(1..30) = 930/61 = 15.2459

  The naive forecast's error is the gap between two independent draws,
  E|X1 - X2| = (N^2 - 1) / (3N) = 3720/183 = 20.3279

  So naive is exactly 4/3 as bad as the best achievable forecast, and no
  model of any sophistication can get below 15.2459.

`check()` confirms both by simulation, and `sampling_spread()` answers the
question the point estimates raise: with only 46 evaluation points, how much
should a measured MAE wobble?
"""

from __future__ import annotations

import math
import random
import statistics

LO, HI = 70, 130
N = HI - LO + 1
TRUE_MEAN = (LO + HI) / 2

CONSTANT_MAE = sum(abs(k - TRUE_MEAN) for k in range(LO, HI + 1)) / N
NAIVE_MAE = (N * N - 1) / (3 * N)


def check(draws: int = 400_000, seed: int = 0) -> dict:
    rng = random.Random(seed)
    xs = [rng.randint(LO, HI) for _ in range(draws)]
    return {
        "constant_sim": statistics.mean(abs(x - TRUE_MEAN) for x in xs),
        "naive_sim": statistics.mean(abs(xs[i] - xs[i - 1]) for i in range(1, draws)),
    }


def sampling_spread(points: int = 46, trials: int = 20_000, seed: int = 1) -> dict:
    """Distribution of the MEASURED naive MAE over `points` forecasts.

    Without this the comparison between a measured 22.93 and a theoretical
    20.33 is unreadable: a gap of 2.6 is either a bug or a Tuesday.
    """
    rng = random.Random(seed)
    maes = []
    for _ in range(trials):
        xs = [rng.randint(LO, HI) for _ in range(points + 1)]
        maes.append(statistics.mean(abs(xs[i] - xs[i - 1]) for i in range(1, len(xs))))
    maes.sort()
    return {
        "mean": statistics.mean(maes),
        "sd": statistics.stdev(maes),
        "p05": maes[int(0.05 * trials)],
        "p95": maes[int(0.95 * trials)],
    }


def main() -> None:
    from series import daily_counts
    from models import naive
    from walkforward import MIN_TRAIN, evaluate, table

    _, values = daily_counts()
    rows = table(values)
    measured = {name: mae for name, mae, _, _ in rows}
    n_eval = len(values) - MIN_TRAIN

    sim = check()
    print("irreducible error, from the known generating process")
    print(f"  best possible (constant 100)  {CONSTANT_MAE:>7.4f}   "
          f"simulated {sim['constant_sim']:>7.3f}")
    print(f"  naive forecast                {NAIVE_MAE:>7.4f}   "
          f"simulated {sim['naive_sim']:>7.3f}")
    print(f"  ratio naive / best            {NAIVE_MAE / CONSTANT_MAE:>7.4f}   "
          f"(exactly 4/3)")

    spread = sampling_spread(points=n_eval)
    print(f"\nmeasured on this series ({n_eval} one-step forecasts)")
    print(f"  historical mean {measured['historical mean']:>6.2f}   "
          f"floor is {CONSTANT_MAE:.2f}; the gap is the cost of estimating "
          f"the mean from {len(values)} days")
    print(f"  naive           {measured['naive']:>6.2f}   theory says "
          f"{NAIVE_MAE:.2f}")
    print(f"\nsampling distribution of naive MAE over {n_eval} forecasts:")
    print(f"  mean {spread['mean']:.2f}, sd {spread['sd']:.2f}, "
          f"90% interval [{spread['p05']:.2f}, {spread['p95']:.2f}]")
    inside = spread["p05"] <= measured["naive"] <= spread["p95"]
    z = (measured["naive"] - spread["mean"]) / spread["sd"]
    print(f"  measured {measured['naive']:.2f} is {z:+.2f} sd from the mean -- "
          f"{'inside' if inside else 'OUTSIDE'} the 90% interval")
    if inside:
        print("\nSo the measured numbers agree with the theory, and the ranking")
        print("is not an artifact of this particular 60 days.")


if __name__ == "__main__":
    main()
