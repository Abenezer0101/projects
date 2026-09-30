"""Sweep BM25's two parameters, because the textbook defaults are a guess.

k1 controls how fast term frequency saturates. b controls how hard long
documents are penalised: b=0 ignores length entirely, b=1 divides by it fully.

The defaults everyone copies are k1=1.5, b=0.75. This measures whether they
are right for a corpus of API documentation, where length is a signal of
thoroughness rather than of padding.
"""

from __future__ import annotations

import search
from evaluate import score
from judgments import JUDGEMENTS
from search import Bm25Index, LikeBaseline, load


def main() -> None:
    docs = load()
    base = score(LikeBaseline(docs), JUDGEMENTS)
    keep_k1, keep_b = search.K1, search.B

    print(f"{'setting':14} {'p@10':>7} {'r@10':>7} {'MRR':>7}")
    print("-" * 40)
    print(f"{'LIKE baseline':14} {base['p@10']:>7.3f} {base['r@10']:>7.3f} {base['mrr']:>7.3f}")
    print()
    search.K1 = 1.5
    for b in (0.0, 0.25, 0.5, 0.75, 1.0):
        search.B = b
        s = score(Bm25Index(docs), JUDGEMENTS)
        note = "  <- textbook default" if b == 0.75 else ""
        print(f"{'b=' + str(b):14} {s['p@10']:>7.3f} {s['r@10']:>7.3f} {s['mrr']:>7.3f}{note}")
    print()
    search.B = 0.25
    for k1 in (0.5, 1.2, 1.5, 2.0, 3.0):
        search.K1 = k1
        s = score(Bm25Index(docs), JUDGEMENTS)
        print(f"{'k1=' + str(k1):14} {s['p@10']:>7.3f} {s['r@10']:>7.3f} {s['mrr']:>7.3f}")

    search.K1, search.B = keep_k1, keep_b
    print("\nb is swept on the same 16 queries the result is reported on, so the")
    print("peak is optimistic. The monotone shape either side of it is not.")


if __name__ == "__main__":
    main()
