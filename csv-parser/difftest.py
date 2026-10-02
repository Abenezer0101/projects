"""Generate adversarial CSV and demand agreement with the `csv` module.

The generator is built from the characters that actually break parsers --
quotes, commas, newlines, CRLF, lone CRs -- in deliberately bad combinations,
rather than from random bytes. Random text almost never produces an unbalanced
quote followed by a delimiter; a generator aimed at the grammar produces one
every few hundred cases.
"""

from __future__ import annotations

import csv
import io
import random
import sys

from parser import naive, parse

# Every one of these is a token a naive split mishandles or a parser
# mis-sequences. The weights are deliberately hostile: a fifth of all
# characters emitted are quotes.
ATOMS = ['a', 'b', '1', ' ', '', ',', '"', '""', '"a"', '\n', '\r\n', '\r',
         '"a,b"', '"a\nb"', '""""', 'a"b', '"ab"c']


def random_csv(rng: random.Random, length: int = 12) -> str:
    return "".join(rng.choice(ATOMS) for _ in range(rng.randrange(1, length)))


def reference(text: str) -> list[list[str]]:
    # newline='' is required: without it io.StringIO still works, but a file
    # opened without it mangles embedded CRLF before csv ever sees it. That
    # single keyword is the most common real-world csv bug.
    return list(csv.reader(io.StringIO(text, newline="")))


def run(trials: int = 50_000, seed: int = 20261003) -> tuple[int, list, int]:
    rng = random.Random(seed)
    failures = []
    naive_wrong = 0
    for _ in range(trials):
        text = random_csv(rng)
        want = reference(text)
        got = parse(text, strip_bom=False)
        if got != want:
            failures.append((text, got, want))
        if naive(text) != want:
            naive_wrong += 1
    return trials, failures, naive_wrong


def main() -> int:
    trials, failures, naive_wrong = run()
    print(f"{trials} generated documents checked against csv.reader")
    print(f"  this parser: {len(failures)} disagreements")
    print(f"  line.split(','): {naive_wrong} disagreements "
          f"({naive_wrong / trials:.1%} of documents)")
    if failures:
        print("\nfirst disagreements:")
        for text, got, want in failures[:10]:
            print(f"  {text!r}\n    got  {got}\n    want {want}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
