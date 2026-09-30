"""Score BM25 against the substring baseline on the hand-labelled set.

Three metrics, because one is easy to flatter:

  precision@10  of the ten results shown, how many are right
  recall@10     of the right answers that exist, how many were shown
  MRR           1/rank of the first correct result, averaged -- this is the
                one a developer feels, since nobody reads past the first hit
                that works
"""

from __future__ import annotations

import sys

from judgments import JUDGEMENTS, validate
from search import Bm25Index, LikeBaseline, load

K = 10


def score(engine, queries: dict[str, set[str]]) -> dict[str, float]:
    p_sum = r_sum = rr_sum = 0.0
    for query, relevant in queries.items():
        got = [doc_id for doc_id, _ in engine.search(query, K)]
        hits = [d for d in got if d in relevant]
        p_sum += len(hits) / K
        r_sum += len(hits) / len(relevant)
        rr_sum += next((1 / (i + 1) for i, d in enumerate(got) if d in relevant), 0.0)
    n = len(queries)
    return {"p@10": p_sum / n, "r@10": r_sum / n, "mrr": rr_sum / n}


def per_query(engines: dict, queries: dict[str, set[str]]) -> None:
    print(f"\n{'query':44} " + " ".join(f"{name:>14}" for name in engines))
    print("-" * (44 + 15 * len(engines)))
    for query, relevant in queries.items():
        cells = []
        for engine in engines.values():
            got = [d for d, _ in engine.search(query, K)]
            hits = sum(1 for d in got if d in relevant)
            rank = next((i + 1 for i, d in enumerate(got) if d in relevant), None)
            cells.append(f"{hits}/{min(len(relevant), K)} @{rank or '-':>3}")
        print(f"{query:44} " + " ".join(f"{c:>14}" for c in cells))


def main() -> int:
    docs = load()
    kept, dropped = validate(docs)
    if dropped:
        print("labelled documents missing from the corpus:")
        for d in dropped:
            print("  ", d)
        return 1
    print(f"{len(docs)} documents, {len(JUDGEMENTS)} queries, {kept} relevance labels")

    engines = {"bm25": Bm25Index(docs), "LIKE": LikeBaseline(docs)}
    print(f"\n{'engine':8} {'p@10':>7} {'r@10':>7} {'MRR':>7}")
    for name, engine in engines.items():
        s = score(engine, JUDGEMENTS)
        print(f"{name:8} {s['p@10']:>7.3f} {s['r@10']:>7.3f} {s['mrr']:>7.3f}")

    per_query(engines, JUDGEMENTS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
