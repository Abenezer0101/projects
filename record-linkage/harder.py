"""A harder set, because the real one is solved by the normaliser.

On the 44 real spellings, normalisation alone scores precision 1.000 and
recall 1.000 -- the corruption there is systematic (case, padding,
abbreviation) and systematic corruption is fixed by rules, not by similarity
scores. Jaro-Winkler contributes nothing.

So this set adds the two things rules cannot fix:

  typos        single-character substitutions, deletions, insertions and
                adjacent transpositions, which no normaliser anticipates
  near-misses  DIFFERENT places with similar names. These are what make a
                threshold a trade-off instead of a free parameter: without
                them, lowering the threshold costs nothing and the "best"
                threshold is always the lowest one.

Generated, from a fixed seed. The ten base names are the real stations; the
corruptions and the decoys are mine.
"""

from __future__ import annotations

import random

BASE = [
    "Atlantic Station", "Centennial Olympic Park", "Georgia State University",
    "Grant Park", "Krog Street Market", "Little Five Points", "Midtown MARTA",
    "Piedmont Park", "Ponce City Market", "West End",
]

# Distinct places whose names sit close to a base name. Each is its own entity
# and must NOT be linked to the name it resembles.
DECOYS = [
    ("Piedmont Place", "Piedmont Park"),
    ("Grand Park", "Grant Park"),
    ("West Endicott", "West End"),
    ("Ponce City Mall", "Ponce City Market"),
    ("Midtown MARTA North", "Midtown MARTA"),
    ("Krog Street Mill", "Krog Street Market"),
]

LETTERS = "abcdefghijklmnopqrstuvwxyz"


def typo(text: str, rng: random.Random) -> str:
    kind = rng.randrange(4)
    if len(text) < 4:
        return text
    i = rng.randrange(1, len(text) - 1)
    if kind == 0:                                    # substitution
        return text[:i] + rng.choice(LETTERS) + text[i + 1:]
    if kind == 1:                                    # deletion
        return text[:i] + text[i + 1:]
    if kind == 2:                                    # insertion
        return text[:i] + rng.choice(LETTERS) + text[i:]
    return text[:i] + text[i + 1] + text[i] + text[i + 2:]   # transposition


def build(seed: int = 0, variants: int = 4) -> tuple[list[str], dict[str, str]]:
    """Returns (records, truth) where truth maps each record to its entity."""
    rng = random.Random(seed)
    truth: dict[str, str] = {}
    for name in BASE:
        truth[name] = name
        for _ in range(variants):
            corrupted = typo(name, rng)
            # a typo that happens to reproduce another entity's name exactly
            # would make the truth map ambiguous; skip those
            if corrupted not in truth:
                truth[corrupted] = name
    for decoy, _resembles in DECOYS:
        truth[decoy] = decoy          # its own entity
    return sorted(truth), truth


def true_pairs(items: list[str], truth: dict[str, str]) -> set[tuple[int, int]]:
    return {(i, j)
            for i in range(len(items)) for j in range(i + 1, len(items))
            if truth[items[i]] == truth[items[j]]}
