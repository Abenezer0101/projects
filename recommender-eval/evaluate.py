"""Three split protocols and one metric, so the only thing that varies is the
protocol.

  random          shuffle every interaction, 80/20. Training sees interactions
                  dated after the ones it is tested on.
  leave-last-out  hold out each user's chronologically last interaction. Per
                  user this looks temporal -- but user A's held-out item may
                  sit in user B's training rows from a later date, so the model
                  still learns from the future. This is the protocol a great
                  many papers use.
  temporal        one global cutoff day. Train is strictly before it, test
                  strictly after. Nothing the model sees postdates anything it
                  is scored on.

Recall@10: of the items a user actually interacted with in the test period,
what fraction appear in their top ten. Items already in the user's training
history are excluded from recommendations -- scoring a model for re-suggesting
something the user has already taken is free marks.
"""

from __future__ import annotations

import random
from collections import defaultdict

from simulate import Interaction

K = 10


def random_split(log: list[Interaction], frac: float = 0.8,
                 seed: int = 0) -> tuple[list, list]:
    shuffled = list(log)
    random.Random(seed).shuffle(shuffled)
    cut = int(len(shuffled) * frac)
    return shuffled[:cut], shuffled[cut:]


def leave_last_out(log: list[Interaction]) -> tuple[list, list]:
    by_user: dict[int, list[Interaction]] = defaultdict(list)
    for i in log:
        by_user[i.user].append(i)
    train, test = [], []
    for user, rows in by_user.items():
        rows = sorted(rows, key=lambda i: i.day)
        if len(rows) < 2:
            train.extend(rows)
            continue
        train.extend(rows[:-1])
        test.append(rows[-1])
    return train, test


def temporal_split(log: list[Interaction], frac: float = 0.8) -> tuple[list, list]:
    """Cutoff chosen so that `frac` of interactions fall before it."""
    days = sorted(i.day for i in log)
    cutoff = days[int(len(days) * frac)]
    train = [i for i in log if i.day < cutoff]
    test = [i for i in log if i.day >= cutoff]
    return train, test


SPLITS = {
    "random": random_split,
    "leave-last-out": leave_last_out,
    "temporal": temporal_split,
}


def recall_at_k(model, train: list[Interaction], test: list[Interaction],
                k: int = K) -> float:
    train_items: dict[int, set[int]] = defaultdict(set)
    for i in train:
        train_items[i.user].add(i.item)
    test_items: dict[int, set[int]] = defaultdict(set)
    for i in test:
        test_items[i.user].add(i.item)

    total_recall, users_scored = 0.0, 0
    for user, relevant in test_items.items():
        recommended = set(model.recommend(user, k, train_items.get(user, set())))
        total_recall += len(recommended & relevant) / len(relevant)
        users_scored += 1
    return total_recall / users_scored if users_scored else 0.0


def run(log: list[Interaction], model_classes) -> dict:
    out: dict[str, dict[str, float]] = {}
    for split_name, splitter in SPLITS.items():
        train, test = splitter(log)
        row = {}
        for cls in model_classes:
            model = cls().fit(train)
            row[model.name] = recall_at_k(model, train, test)
        out[split_name] = row
    return out


def main() -> None:
    from collections import defaultdict

    from models import MODELS
    from simulate import generate

    log = generate(drift=1.0)
    results = run(log, MODELS)
    names = list(results["random"].keys())

    print("recall@10 under each protocol (drift = 1.0)\n")
    print(f"{'protocol':18}" + "".join(f"{n:>26}" for n in names))
    print("-" * (18 + 26 * len(names)))
    for split in SPLITS:
        print(f"{split:18}" + "".join(f"{results[split][n]:>26.3f}" for n in names))

    print("\nwhy those rows are not comparable: the protocols pose different tasks\n")
    print(f"  {'protocol':18} {'relevant/test user':>19} {'cold-start users':>18}")
    for split, splitter in SPLITS.items():
        train, test = splitter(log)
        by_user = defaultdict(set)
        for i in test:
            by_user[i.user].add(i.item)
        mean_relevant = sum(len(v) for v in by_user.values()) / len(by_user)
        trained = {i.user for i in train}
        cold = len({i.user for i in test} - trained) / len(by_user)
        print(f"  {split:18} {mean_relevant:>19.2f} {cold:>17.0%}")
    print("\nSee controlled.py for the experiment that holds the task fixed.")


if __name__ == "__main__":
    main()
