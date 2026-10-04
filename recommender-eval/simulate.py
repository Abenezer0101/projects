"""An interaction log with a dial for temporal drift.

The claim under test is about an evaluation PROTOCOL, not about any catalogue:
splitting interactions at random leaks the future into training and inflates
offline scores. To show that is the cause rather than a coincidence, the
generator exposes the one ingredient responsible -- how much item popularity
moves over time -- so the same experiment can be run with the mechanism turned
off. At drift = 0 the two protocols must agree; if they disagree there, the
harness is broken, not the protocol.

The log is generated. The repository's real ratings table holds 24 rows, which
is three orders of magnitude short of an evaluation set, and no public
interaction dataset is reachable from this environment.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

N_USERS = 2_000
N_ITEMS = 500
N_DAYS = 120
PER_USER = (5, 40)


@dataclass(frozen=True)
class Interaction:
    user: int
    item: int
    day: int


def item_appeal(rng: random.Random, n_items: int) -> list[float]:
    """Static quality, Zipf-ish but flatter than a strict 1/rank.

    The exponent matters. At 1.1 the head items are ~350x the tail and no
    amount of trending can displace them, so the drift dial did nothing in the
    first version of this file -- the top-10 overlap between the first and last
    quarter stayed at 9/10 for every setting. At 0.5 a trending item can
    actually reach the chart, which is what real catalogues do.
    """
    return [1.0 / (rank + 2) ** 0.5 for rank in range(n_items)]


def popularity_at(day: int, item: int, appeal: list[float], drift: float,
                  n_days: int) -> float:
    """Item weight on a given day.

    With drift = 0 this is the item's static appeal and the log is stationary.
    With drift > 0 each item gets a smooth rise-and-fall centred on its own
    peak day, so what is popular in week 2 is not what is popular in week 16 --
    which is exactly what a random split lets a model peek at.
    """
    base = appeal[item]
    if drift <= 0:
        return base
    peak = (item * 7919) % n_days            # deterministic, spread out
    width = n_days / 6
    bump = math.exp(-((day - peak) ** 2) / (2 * width * width))
    # The multiplier was chosen by sweeping it: at 20 even drift=0.25 fully
    # reorders the chart, which gives no gradient to measure along. At 2 the
    # top-10 overlap between the first and last quarter runs 9, 9, 6, 1, 0 for
    # drift 0, 0.5, 1, 2, 4 -- a dial rather than a switch.
    return base * (1.0 + 2.0 * drift * bump)


def generate(drift: float = 1.0, seed: int = 0, n_users: int = N_USERS,
             n_items: int = N_ITEMS, n_days: int = N_DAYS) -> list[Interaction]:
    rng = random.Random(seed)
    appeal = item_appeal(rng, n_items)

    # Precompute per-day sampling weights once: 120 days x 500 items is cheap,
    # and resampling per interaction would dominate the runtime.
    weights_by_day = [
        [popularity_at(day, item, appeal, drift, n_days) for item in range(n_items)]
        for day in range(n_days)
    ]
    items = list(range(n_items))

    log: list[Interaction] = []
    for user in range(n_users):
        # each user is active in one window, as real users are
        start = rng.randrange(n_days)
        span = rng.randrange(1, 30)
        count = rng.randint(*PER_USER)
        seen: set[int] = set()
        for _ in range(count):
            day = min(n_days - 1, start + rng.randrange(span + 1))
            item = rng.choices(items, weights=weights_by_day[day], k=1)[0]
            if item in seen:
                continue           # one interaction per user-item pair
            seen.add(item)
            log.append(Interaction(user, item, day))
    log.sort(key=lambda i: (i.day, i.user, i.item))
    return log


def describe(log: list[Interaction]) -> dict:
    users = {i.user for i in log}
    items = {i.item for i in log}
    return {
        "interactions": len(log),
        "users": len(users),
        "items": len(items),
        "days": max(i.day for i in log) + 1,
        "density": len(log) / (len(users) * len(items)),
    }
