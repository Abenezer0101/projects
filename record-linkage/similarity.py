"""Jaro and Jaro-Winkler, from the definitions.

Jaro similarity of two strings:

    0                                        if m = 0
    (m/|s1| + m/|s2| + (m-t)/m) / 3          otherwise

where m is the number of matching characters -- characters that appear in both
strings within a window of floor(max(|s1|,|s2|)/2) - 1 positions -- and t is
half the number of transpositions among those matches.

Jaro-Winkler then rewards a shared prefix:

    jw = jaro + l * p * (1 - jaro)

with l the common prefix length capped at 4 and p = 0.1. The prefix bonus is
why it suits names: people and places are misspelled at the end far more often
than at the start.

Validated against the standard published values in the tests -- MARTHA/MARHTA
= 0.961, DIXON/DICKSONX = 0.813, JELLYFISH/SMELLYFISH = 0.896.
"""

from __future__ import annotations

PREFIX_WEIGHT = 0.1
MAX_PREFIX = 4


def jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    # the window is intentionally floor(max/2) - 1, not max/2: the off-by-one
    # changes the score on short strings and is the usual implementation bug
    window = max(len1, len2) // 2 - 1
    if window < 0:
        window = 0

    s1_matched = [False] * len1
    s2_matched = [False] * len2

    matches = 0
    for i, ch in enumerate(s1):
        lo = max(0, i - window)
        hi = min(i + window + 1, len2)
        for j in range(lo, hi):
            if s2_matched[j] or s2[j] != ch:
                continue
            s1_matched[i] = s2_matched[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    # transpositions: matched characters that appear in a different order
    transpositions = 0
    j = 0
    for i in range(len1):
        if not s1_matched[i]:
            continue
        while not s2_matched[j]:
            j += 1
        if s1[i] != s2[j]:
            transpositions += 1
        j += 1
    transpositions //= 2

    return (matches / len1
            + matches / len2
            + (matches - transpositions) / matches) / 3


def jaro_winkler(s1: str, s2: str, prefix_weight: float = PREFIX_WEIGHT) -> float:
    score = jaro(s1, s2)
    if score == 0.0:
        return 0.0
    prefix = 0
    for a, b in zip(s1[:MAX_PREFIX], s2[:MAX_PREFIX]):
        if a != b:
            break
        prefix += 1
    return score + prefix * prefix_weight * (1 - score)
