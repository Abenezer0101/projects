"""Inject known anomalies, then score each detector on finding them.

Three kinds, because they separate the detectors:

  global spike     far above anything the series ever does. Everyone should
                   find these; a detector that misses them is broken.
  contextual spike a value that is unremarkable in absolute terms and absurd
                   for its hour -- 12 trips at 03:00, which is normal at 08:00.
  dropout          zero trips at 08:00. Zero happens constantly at 03:00, so
                   nothing flags it without knowing the time of day.

Precision and recall are both reported. A detector that flags 8% of all points
will catch most anomalies and be useless, and recall alone would hide that.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from detectors import DETECTORS
from series import hourly_counts

QUIET_HOURS = (0, 1, 2, 3, 4, 23)
BUSY_HOURS = (7, 8, 17, 18)


@dataclass
class Injected:
    values: list[float]
    truth: set[int]
    kinds: dict[int, str]


def inject(values: list[float], stamps, seed: int = 0, n_each: int = 12) -> Injected:
    rng = random.Random(seed)
    out = list(values)
    truth: set[int] = set()
    kinds: dict[int, str] = {}

    quiet = [i for i, s in enumerate(stamps) if s.hour in QUIET_HOURS]
    busy = [i for i, s in enumerate(stamps) if s.hour in BUSY_HOURS]
    anywhere = list(range(len(values)))

    for index in rng.sample(anywhere, n_each):
        out[index] = 60.0
        truth.add(index)
        kinds[index] = "global spike"
    for index in rng.sample([i for i in quiet if i not in truth], n_each):
        out[index] = 12.0
        truth.add(index)
        kinds[index] = "contextual spike"
    for index in rng.sample([i for i in busy if i not in truth], n_each):
        out[index] = 0.0
        truth.add(index)
        kinds[index] = "dropout"
    return Injected(out, truth, kinds)


def score(flagged: set[int], truth: set[int], total: int) -> dict:
    hits = flagged & truth
    precision = len(hits) / len(flagged) if flagged else 0.0
    recall = len(hits) / len(truth) if truth else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {"flagged": len(flagged), "precision": precision, "recall": recall, "f1": f1}


def by_kind(flagged: set[int], data: Injected) -> dict[str, tuple[int, int]]:
    out: dict[str, list[int]] = {}
    for index, kind in data.kinds.items():
        found, total = out.setdefault(kind, [0, 0])
        out[kind] = [found + (1 if index in flagged else 0), total + 1]
    return {k: (v[0], v[1]) for k, v in out.items()}


def main() -> None:
    stamps, clean = hourly_counts()
    data = inject(clean, stamps)
    print(f"{len(clean)} hourly points, {len(data.truth)} injected anomalies "
          f"({len(data.truth) / len(clean):.1%} of the series)\n")

    print(f"{'detector':26} {'flags':>6} {'precision':>10} {'recall':>8} {'F1':>7}")
    print("-" * 62)
    rows = []
    for cls in DETECTORS:
        d = cls()
        flagged = d.flag(data.values)
        s = score(flagged, data.truth, len(data.values))
        rows.append((d.name, flagged, s))
        print(f"{d.name:26} {s['flagged']:>6} {s['precision']:>9.1%} "
              f"{s['recall']:>8.1%} {s['f1']:>7.3f}")

    print(f"\nrecall by anomaly kind")
    kinds = ["global spike", "contextual spike", "dropout"]
    print(f"  {'detector':26} " + " ".join(f"{k:>18}" for k in kinds))
    for name, flagged, _ in rows:
        found = by_kind(flagged, data)
        cells = " ".join(f"{found[k][0]:>10}/{found[k][1]:<7}" for k in kinds)
        print(f"  {name:26} {cells}")

    print("\nDropouts are the test that matters: a zero is the single commonest")
    print("value in this series (240 of 1438 points), so only a detector that")
    print("knows 08:00 from 03:00 can call one an anomaly.")


if __name__ == "__main__":
    main()
