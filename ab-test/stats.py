"""Two-proportion test, and an exact binomial sampler fast enough to simulate with.

Nothing here is novel. It exists so the simulation in `peeking.py` is exact
rather than an approximation of the thing it is trying to measure -- a study
of false-positive rates that itself used a normal approximation to generate
its data would be measuring the approximation.
"""

from __future__ import annotations

import bisect
import math
import random

SQRT2 = math.sqrt(2.0)


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / SQRT2))


def two_sided_p(z: float) -> float:
    return 2.0 * (1.0 - normal_cdf(abs(z)))


def z_score(x_a: int, n_a: int, x_b: int, n_b: int) -> float:
    """Pooled two-proportion z. Returns 0.0 when it is undefined.

    Undefined happens for real: on day one of a low-rate test both arms can
    sit at zero conversions, and a test that raises there would be a test
    nobody could run.
    """
    if n_a == 0 or n_b == 0:
        return 0.0
    p_pool = (x_a + x_b) / (n_a + n_b)
    if p_pool <= 0.0 or p_pool >= 1.0:
        return 0.0
    se = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_a + 1.0 / n_b))
    return (x_a / n_a - x_b / n_b) / se


class BinomialSampler:
    """Exact Binomial(n, p) draws by inverse transform on a precomputed CDF.

    Looping over n Bernoulli trials is exact but far too slow to run millions
    of simulated experiments; a normal approximation is fast but changes the
    tail behaviour, which is exactly what is being measured. Precomputing the
    CDF once costs O(n) and makes every draw an O(log n) bisect of a uniform,
    exact to the floating-point representation of the pmf.
    """

    def __init__(self, n: int, p: float):
        self.n, self.p = n, p
        cdf: list[float] = []
        total = 0.0
        # pmf by the recurrence rather than math.comb: 1000-choose-500 is a
        # 300-digit integer and the ratio form never leaves float range
        pmf = (1.0 - p) ** n if p < 1.0 else 0.0
        for k in range(n + 1):
            total += pmf
            cdf.append(total)
            if k < n and p < 1.0:
                pmf *= (n - k) / (k + 1) * (p / (1.0 - p))
        # guard the last entry against accumulated error so a uniform of
        # 0.9999999 can never fall off the end
        cdf[-1] = 1.0
        self.cdf = cdf

    def draw(self, rng: random.Random) -> int:
        return bisect.bisect_left(self.cdf, rng.random())
