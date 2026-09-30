"""An inverted index with BM25, and the substring baseline it has to beat.

BM25 scores a document for a query as the sum over query terms of

    IDF(t) * f(t,d) * (k1 + 1) / (f(t,d) + k1 * (1 - b + b * |d| / avgdl))

Two ideas are doing all the work. Term frequency saturates, so a document
repeating a word twenty times is not twenty times more relevant than one
using it once -- that is the k1 term. And length is normalised, so a long
document does not win merely by containing more words -- that is b.

The baseline is `WHERE text LIKE '%term%'`, which is what a search feature
looks like before someone decides to do it properly.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict

K1 = 1.5
# The textbook default is b=0.75. On this corpus that is actively harmful:
# docstring length correlates with how thorough the documentation is, so
# penalising length demotes argparse.ArgumentParser -- which documents every
# keyword argument -- below argparse.Action, which is shorter and says less.
# sweep.py measures the whole curve; 0.25 is its peak. See the README for why
# that number should be read with suspicion.
B = 0.25

TOKEN = re.compile(r"[a-z0-9]+")

# Stopping at a short list rather than a linguistic one: these carry no
# discriminating power in English prose and every one of them appears in
# hundreds of docstrings.
STOP = frozenset("""a an and are as at be by for from has have if in into is it
its of on or that the to with will this these those was were been""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP and len(t) > 1]


class Bm25Index:
    def __init__(self, docs: list[dict]):
        self.docs = docs
        self.postings: dict[str, dict[int, int]] = defaultdict(dict)
        self.lengths: list[int] = []
        for i, doc in enumerate(docs):
            terms = tokenize(doc["text"] + " " + doc["id"].replace(".", " "))
            self.lengths.append(len(terms))
            for term, freq in Counter(terms).items():
                self.postings[term][i] = freq
        self.avgdl = sum(self.lengths) / len(self.lengths)
        self.n = len(docs)

    def idf(self, term: str) -> float:
        df = len(self.postings.get(term, ()))
        if not df:
            return 0.0
        # the +0.5 smoothing is Robertson-Sparck Jones; without the max() a
        # term in more than half the corpus would score negative and a
        # document could be punished for containing a query word
        return max(1e-9, math.log(1 + (self.n - df + 0.5) / (df + 0.5)))

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        scores: dict[int, float] = defaultdict(float)
        for term in tokenize(query):
            idf = self.idf(term)
            if not idf:
                continue
            for i, freq in self.postings[term].items():
                norm = 1 - B + B * self.lengths[i] / self.avgdl
                scores[i] += idf * freq * (K1 + 1) / (freq + K1 * norm)
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], self.docs[kv[0]]["id"]))
        return [(self.docs[i]["id"], s) for i, s in ranked[:k]]


class LikeBaseline:
    """`WHERE text LIKE '%t1%' OR ... ` -- match anywhere, rank by match count.

    Giving it the OR and a count-based ranking is deliberately generous; the
    literal SQL version returns rows in whatever order the table yields them,
    which would score even worse.
    """

    def __init__(self, docs: list[dict]):
        self.docs = docs
        self.blobs = [(d["id"], (d["text"] + " " + d["id"]).lower()) for d in docs]

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        terms = tokenize(query)
        hits = []
        for doc_id, blob in self.blobs:
            n = sum(1 for t in terms if t in blob)
            if n:
                hits.append((doc_id, float(n)))
        hits.sort(key=lambda kv: (-kv[1], kv[0]))
        return hits[:k]


def load(path: str = "corpus.json") -> list[dict]:
    with open(path) as fh:
        return json.load(fh)
