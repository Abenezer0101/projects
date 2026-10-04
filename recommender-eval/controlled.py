"""The controlled experiment: hold the test set fixed and vary only the leak.

Comparing recall across the three protocols in evaluate.py does not work, and
the reason is worth stating because it is the same mistake that makes published
comparisons incomparable. The protocols do not produce three measurements of
one task; they produce three different tasks:

  protocol         relevant items per test user    cold-start test users
  random                   4.47                          0%
  leave-last-out           1.00                          0%
  temporal                16.67                         58%

Recall@10 against one relevant item is a far easier number than recall@10
against seventeen, and a model facing 58% users it has never seen is doing
something else entirely. Under those conditions the temporal protocol scored
HIGHER than the random one -- not because leaking the future hurts, but
because the two tasks were never the same.

So this file changes one thing at a time. The test set is the temporal one
and never moves. Training is either everything before the cutoff (honest) or a
random sample of the SAME SIZE drawn from everywhere except the test rows
themselves (leaky). Same test items, same training volume, same model, same
metric. Whatever difference remains is the leak.
"""

from __future__ import annotations

import random

from evaluate import K, recall_at_k, temporal_split
from models import MODELS
from simulate import Interaction, generate


def honest_and_leaky(log: list[Interaction], frac: float = 0.8,
                     seed: int = 0, test_frac: float = 0.25
                     ) -> tuple[list, list, list]:
    """Returns (test, honest_train, leaky_train), the two trains equal in size.

    Getting this wrong is instructive. The first version built the leaky
    training set by sampling everything EXCEPT the test rows -- which deletes
    the test period's other rows, the exact thing a random split leaks. It
    measured an inflation of 1.00x across every drift setting, because there
    was no leak left to measure.

    What a random split actually does is hold out a FRACTION of the test
    period and train on the rest of it. So the test set here is a random
    quarter of the post-cutoff rows, and the leaky training set may draw on
    the other three quarters -- rows contemporaneous with the test, which the
    honest training set cannot see.
    """
    pre, post = temporal_split(log, frac)
    rng = random.Random(seed)
    post_shuffled = list(post)
    rng.shuffle(post_shuffled)
    cut = int(len(post_shuffled) * test_frac)
    test, leftover_post = post_shuffled[:cut], post_shuffled[cut:]

    size = min(len(pre), len(pre) + len(leftover_post))
    honest_train = rng.sample(pre, size)
    leaky_train = rng.sample(pre + leftover_post, size)
    return test, honest_train, leaky_train


def compare(log: list[Interaction], seed: int = 0) -> dict:
    test, honest_train, leaky_train = honest_and_leaky(log, seed=seed)
    out = {}
    for cls in MODELS:
        honest = recall_at_k(cls().fit(honest_train), honest_train, test, K)
        # NOTE: the exclude set must come from the SAME training rows the model
        # saw, or the leaky run would be handed a different task again.
        leaky = recall_at_k(cls().fit(leaky_train), leaky_train, test, K)
        out[cls().name] = {
            "honest": honest,
            "leaky": leaky,
            "inflation": leaky / honest if honest else float("nan"),
        }
    return out, len(test), len(honest_train), len(leaky_train)


def main() -> None:
    log = generate(drift=1.0)
    result, n_test, n_honest, n_leaky = compare(log)
    print(f"test interactions {n_test}, honest train {n_honest}, "
          f"leaky train {n_leaky} (same size)\n")
    print(f"{'model':26} {'honest':>8} {'leaky':>8} {'inflation':>10}")
    print("-" * 56)
    for name, r in result.items():
        print(f"{name:26} {r['honest']:>8.3f} {r['leaky']:>8.3f} "
              f"{r['inflation']:>9.2f}x")

    print("\ndrift sweep -- inflation should vanish when popularity stops moving")
    print(f"  {'drift':>6} " + " ".join(f"{cls().name[:18]:>19}" for cls in MODELS))
    for drift in (0.0, 0.5, 1.0, 2.0, 4.0):
        row, *_ = compare(generate(drift=drift))
        cells = " ".join(f"{row[cls().name]['inflation']:>18.2f}x" for cls in MODELS)
        print(f"  {drift:>6.1f} {cells}")


if __name__ == "__main__":
    main()


def ranking_flips(drift: float = 1.0, seeds: int = 25) -> dict:
    """Does the leak change WHICH model you would ship?

    Inflation that lifted every model equally would be harmless -- you would
    still pick the same one. This counts how often the honest winner and the
    leaky winner disagree.
    """
    flips = 0
    honest_winners: dict[str, int] = {}
    leaky_winners: dict[str, int] = {}
    for seed in range(seeds):
        row, *_ = compare(generate(drift=drift, seed=seed), seed=seed)
        honest_best = max(row, key=lambda n: row[n]["honest"])
        leaky_best = max(row, key=lambda n: row[n]["leaky"])
        honest_winners[honest_best] = honest_winners.get(honest_best, 0) + 1
        leaky_winners[leaky_best] = leaky_winners.get(leaky_best, 0) + 1
        if honest_best != leaky_best:
            flips += 1
    return {"seeds": seeds, "flips": flips,
            "honest_winners": honest_winners, "leaky_winners": leaky_winners}
