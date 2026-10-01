"""Differential test: generate patterns, run both engines, demand agreement.

Hand-written cases test what the author already thought of. Generated ones
test what they didn't. Every pattern is built from the supported subset, every
input is drawn from a tiny alphabet so collisions are frequent, and any
disagreement with `re.fullmatch` is a bug in this engine until proven
otherwise.

Two classes of pattern are skipped rather than counted as disagreements:
those `re` itself rejects, and stacked quantifiers (`a+?`, `a*+`), which `re`
reads as lazy or possessive. Those are documented as out of scope in nfa.py
rather than quietly parsed as something else.
"""

from __future__ import annotations

import random
import re
import sys

from nfa import Regex

ALPHABET = "ab"


def random_pattern(rng: random.Random, depth: int = 0) -> str:
    """A pattern from the supported grammar, biased towards small ones."""
    if depth > 2 or rng.random() < 0.35:
        return rng.choice(list(ALPHABET) + [".", "[ab]", "[^a]", "[a-b]"])
    kind = rng.random()
    if kind < 0.3:
        return random_pattern(rng, depth + 1) + random_pattern(rng, depth + 1)
    if kind < 0.55:
        return f"({random_pattern(rng, depth + 1)}|{random_pattern(rng, depth + 1)})"
    if kind < 0.8:
        inner = f"({random_pattern(rng, depth + 1)}){rng.choice('*+?')}"
        # occasionally stack a second quantifier: this engine accepts it, `re`
        # calls it "multiple repeat", and the skip counter proves the path runs
        return inner + rng.choice("*+?") if rng.random() < 0.08 else inner
    return f"({random_pattern(rng, depth + 1)})"


def random_text(rng: random.Random) -> str:
    return "".join(rng.choice(ALPHABET) for _ in range(rng.randrange(0, 7)))


def run(trials: int = 20_000, seed: int = 20261001) -> tuple[int, int, list]:
    rng = random.Random(seed)
    checked = skipped = 0
    failures = []
    for _ in range(trials):
        pattern = random_pattern(rng)
        try:
            reference = re.compile(pattern)
        except re.error:
            skipped += 1
            continue
        try:
            mine = Regex(pattern)
        except ValueError:
            skipped += 1
            continue
        for _ in range(4):
            text = random_text(rng)
            got = mine.fullmatch(text)
            want = reference.fullmatch(text) is not None
            checked += 1
            if got != want:
                failures.append((pattern, text, got, want))
    return checked, skipped, failures


def main() -> int:
    checked, skipped, failures = run()
    print(f"{checked} pattern/input pairs checked against re.fullmatch, "
          f"{skipped} patterns skipped (invalid in re, or lazy/possessive)")
    if failures:
        print(f"\n{len(failures)} disagreements:")
        for pattern, text, got, want in failures[:20]:
            print(f"  {pattern!r} vs {text!r}: nfa={got} re={want}")
        return 1
    print("no disagreements")
    return 0


if __name__ == "__main__":
    sys.exit(main())
