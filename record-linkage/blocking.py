"""Blocking: cut the pair count before any matcher runs, and pay for it.

Comparing every pair is quadratic -- 44 records is 946 pairs, 100,000 records
is 5 billion. Blocking only compares records that share a cheap key.

Two numbers describe a blocking scheme, and reporting only the first is the
usual mistake:

  reduction ratio    1 - candidate pairs / all pairs. How much work is saved.
  pair completeness  true matches retained / all true matches. This is a HARD
                     CEILING on recall: a true pair that blocking discards can
                     never be recovered by any threshold or any matcher.

A scheme with a 99% reduction ratio and 60% pair completeness has thrown away
two fifths of the answer, and the matcher's recall curve will top out at 0.6
with no indication of why.
"""

from __future__ import annotations

import re
from collections import defaultdict

ABBREVIATIONS = {"pk": "park", "st": "street", "ave": "avenue", "rd": "road"}


def normalise(value: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation, expand abbreviations.

    The abbreviation step uses a lookahead-free word match rather than an
    end-anchored pattern. The Day 13 project's bug was exactly that: `\\bSt\\.$`
    expanded "Main St." and never "Krog St. Market", where the abbreviation
    sits mid-string.
    """
    text = value.lower().strip()
    text = re.sub(r"[.,]", " ", text)
    tokens = [ABBREVIATIONS.get(t, t) for t in text.split()]
    return " ".join(tokens)


def no_blocking(items: list[str]) -> set[tuple[int, int]]:
    return {(i, j) for i in range(len(items)) for j in range(i + 1, len(items))}


def _from_keys(items: list[str], key) -> set[tuple[int, int]]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for i, item in enumerate(items):
        buckets[key(item)].append(i)
    pairs = set()
    for indices in buckets.values():
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                pairs.add(tuple(sorted((indices[a], indices[b]))))
    return pairs


def first_letter_raw(items: list[str]) -> set[tuple[int, int]]:
    """Block on the first character of the RAW string.

    The tempting one-liner, and a trap: '  Krog Street Market ' starts with a
    space and 'KROG STREET MARKET' with 'K', so they land in different blocks
    and are never compared.
    """
    return _from_keys(items, lambda s: s[:1])


def first_letter_normalised(items: list[str]) -> set[tuple[int, int]]:
    return _from_keys(items, lambda s: normalise(s)[:1])


def first_three_normalised(items: list[str]) -> set[tuple[int, int]]:
    return _from_keys(items, lambda s: normalise(s)[:3])


def token_sorted(items: list[str]) -> set[tuple[int, int]]:
    """Block on the first letter of each sorted token -- a crude 'sorted
    neighbourhood'. Tolerates word order and most single-token damage."""
    return _from_keys(items,
                      lambda s: "".join(sorted(t[0] for t in normalise(s).split())))


def length_bucket(items: list[str]) -> set[tuple[int, int]]:
    """Block on normalised length / 4. Fast, and blind to abbreviation:
    'grant park' is 10 characters and 'grant pk' normalises to the same
    string, but a genuine abbreviation that does NOT expand changes bucket."""
    return _from_keys(items, lambda s: str(len(normalise(s)) // 4))


SCHEMES = {
    "none (all pairs)": no_blocking,
    "first letter, raw": first_letter_raw,
    "first letter, normalised": first_letter_normalised,
    "first 3 chars, normalised": first_three_normalised,
    "sorted token initials": token_sorted,
    "length bucket": length_bucket,
}


def assess(items: list[str], truth: set[tuple[int, int]], scheme) -> dict:
    candidates = scheme(items)
    total = len(items) * (len(items) - 1) // 2
    retained = candidates & truth
    return {
        "candidates": len(candidates),
        "reduction": 1 - len(candidates) / total,
        "completeness": len(retained) / len(truth) if truth else 1.0,
    }
