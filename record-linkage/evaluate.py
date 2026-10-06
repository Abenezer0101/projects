"""Score linkage against the labelled truth, and sweep the threshold.

Two datasets, because they say different things:

  real    44 spellings of 10 stations from the committed trips file. The
          corruption is systematic, and the normaliser alone solves it.
  harder  typos and near-miss decoys. Rules cannot reach these, which is
          where a similarity score earns its keep -- and where a threshold
          becomes a real trade-off rather than a free parameter.
"""

from __future__ import annotations

from blocking import SCHEMES, assess, first_three_normalised, normalise
from records import records as real_records
from records import true_pairs as real_true_pairs
from similarity import jaro_winkler

import harder


def predict(items: list[str], threshold: float, block=first_three_normalised,
            use_normalise: bool = True) -> set[tuple[int, int]]:
    """Candidate pairs from blocking, scored by Jaro-Winkler, cut at threshold."""
    prepared = [normalise(s) if use_normalise else s for s in items]
    return {(i, j) for (i, j) in block(items)
            if jaro_winkler(prepared[i], prepared[j]) >= threshold}


def score(predicted: set, truth: set) -> dict:
    hits = predicted & truth
    precision = len(hits) / len(predicted) if predicted else 0.0
    recall = len(hits) / len(truth) if truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"predicted": len(predicted), "precision": precision,
            "recall": recall, "f1": f1}


def sweep(items: list[str], truth: set, block=first_three_normalised) -> list[tuple]:
    rows = []
    for step in range(10, 21):
        threshold = step / 20          # 0.50 .. 1.00
        s = score(predict(items, threshold, block), truth)
        rows.append((threshold, s))
    return rows


def main() -> None:
    real = real_records()
    real_truth = real_true_pairs(real)

    print("blocking on the 44 real spellings")
    print(f"  {'scheme':28} {'pairs':>7} {'reduction':>10} {'completeness':>13}")
    for name, fn in SCHEMES.items():
        a = assess(real, real_truth, fn)
        flag = "" if a["completeness"] == 1.0 else "  <- caps recall"
        print(f"  {name:28} {a['candidates']:>7} {a['reduction']:>9.1%} "
              f"{a['completeness']:>12.1%}{flag}")

    exact = {(i, j) for i in range(len(real)) for j in range(i + 1, len(real))
             if normalise(real[i]) == normalise(real[j])}
    s = score(exact, real_truth)
    print(f"\nnormalisation alone, no similarity score at all:")
    print(f"  precision {s['precision']:.3f}  recall {s['recall']:.3f}  "
          f"F1 {s['f1']:.3f}")
    print("  The corruption here is systematic, so a rule fixes it exactly and")
    print("  Jaro-Winkler has nothing left to contribute.")

    items, truth_map = harder.build()
    truth = harder.true_pairs(items, truth_map)
    exact_hard = {(i, j) for i in range(len(items)) for j in range(i + 1, len(items))
                  if normalise(items[i]) == normalise(items[j])}
    sh = score(exact_hard, truth)
    print(f"\nsame rule on the harder set ({len(items)} records, "
          f"{len(set(truth_map.values()))} entities):")
    print(f"  precision {sh['precision']:.3f}  recall {sh['recall']:.3f}  "
          f"F1 {sh['f1']:.3f}   <- rules cannot reach a typo")

    print(f"\nJaro-Winkler threshold sweep on the harder set")
    print(f"  {'threshold':>10} {'pairs':>7} {'precision':>10} {'recall':>8} {'F1':>7}")
    best = (None, -1.0)
    for threshold, s in sweep(items, truth):
        if s["f1"] > best[1]:
            best = (threshold, s["f1"])
        print(f"  {threshold:>10.2f} {s['predicted']:>7} {s['precision']:>9.1%} "
              f"{s['recall']:>8.1%} {s['f1']:>7.3f}")
    print(f"\n  best F1 {best[1]:.3f} at threshold {best[0]:.2f}")


if __name__ == "__main__":
    main()
