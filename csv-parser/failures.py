"""Where exactly does `line.split(",")` go wrong, and how often?

Two corpora, because one number alone would be dishonest:

  adversarial -- the hostile generator from difftest.py, a fifth of whose
                 characters are quotes. Useful for finding parser bugs,
                 useless as an estimate of real-world risk.
  realistic   -- rows of plausible data where only some fields are quoted,
                 at rates taken from what spreadsheet exports actually emit:
                 free-text fields with commas, the occasional address with a
                 newline, a CRLF file ending.

Each failing document is classified by the first cause that applies, so the
table says which feature did the damage rather than just that something did.
"""

from __future__ import annotations

import csv
import io
import random
from collections import Counter

from difftest import random_csv, reference
from parser import naive, parse

FIRST_NAMES = ["Abenezer", "Dana", "Yusuf", "Mei", "Olu", "Ines"]
NOTES = [
    "fine",
    "called back, no answer",            # a comma: the common case
    'said "maybe next quarter"',         # quotes
    "line one\nline two",                # embedded newline
    "",                                  # empty
    "1,250.00",                          # a number with a thousands separator
]


def realistic_csv(rng: random.Random, rows: int = 8) -> str:
    newline = "\r\n" if rng.random() < 0.4 else "\n"
    out = ["id,name,note,amount"]
    for i in range(rows):
        note = rng.choice(NOTES)
        # a producer quotes a field only when it has to
        if any(c in note for c in ',"\n'):
            note = '"' + note.replace('"', '""') + '"'
        out.append(f"{i},{rng.choice(FIRST_NAMES)},{note},{rng.randrange(100)}")
    return newline.join(out) + newline


def classify(text: str, got: list, want: list) -> str:
    """First cause that applies. Order matters: the earlier causes subsume."""
    if len(got) != len(want):
        if any("\n" in f or "\r" in f for row in want for f in row):
            return "newline inside a quoted field split one row into two"
        return "row count differs"
    for g, w in zip(got, want):
        if len(g) != len(w):
            if any("," in f for f in w):
                return "comma inside a quoted field invented a column"
            if not w:
                return "blank line read as one empty field"
            return "field count differs"
    for g, w in zip(got, want):
        for gf, wf in zip(g, w):
            if gf != wf:
                if gf == f'"{wf}"':
                    return "quotes left in the value"
                if '""' in gf:
                    return "escaped quote not unescaped"
                return "field value differs"
    return "unclassified"


def survey(label: str, make, trials: int, seed: int) -> None:
    rng = random.Random(seed)
    causes: Counter[str] = Counter()
    mine_wrong = 0
    for _ in range(trials):
        text = make(rng)
        want = reference(text)
        if parse(text, strip_bom=False) != want:
            mine_wrong += 1
        got = naive(text)
        if got != want:
            causes[classify(text, got, want)] += 1
    bad = sum(causes.values())
    print(f"\n{label}: {trials} documents")
    print(f"  this parser wrong: {mine_wrong}")
    print(f"  line.split(',') wrong: {bad} ({bad / trials:.1%})")
    for cause, n in causes.most_common():
        print(f"    {n / trials:>6.1%}  {cause}")


def main() -> None:
    survey("adversarial", random_csv, 20_000, seed=1)
    survey("realistic", realistic_csv, 20_000, seed=2)
    sweep()




def sweep(trials: int = 4000, rows: int = 8, seed: int = 3) -> None:
    """How often one bad field anywhere ruins the whole file.

    A flat "100% of realistic files break" is a rigged number -- it depends
    entirely on how often your data contains a comma or a newline. So vary
    that rate and watch the per-file rate, which should follow

        P(file wrong) = 1 - (1 - p) ** rows

    because a single mishandled field is enough. That compounding is the real
    point: a 5% per-field hazard is a 34% per-file hazard at eight rows, and
    nobody ships an eight-row file.
    """
    rng = random.Random(seed)
    print(f"\nper-field hazard vs per-file failure ({rows} rows, {trials} files each)")
    print(f"  {'p(field)':>9} {'measured':>9} {'1-(1-p)^n':>11}")
    for p in (0.0, 0.01, 0.02, 0.05, 0.10, 0.25, 0.50):
        wrong = 0
        for _ in range(trials):
            out = ["id,name,note"]
            for i in range(rows):
                note = "fine"
                if rng.random() < p:
                    note = '"' + rng.choice(["a,b", "a\nb"]) + '"'
                out.append(f"{i},{rng.choice(FIRST_NAMES)},{note}")
            text = "\n".join(out) + "\n"
            if naive(text) != reference(text):
                wrong += 1
        predicted = 1 - (1 - p) ** rows
        print(f"  {p:>9.2f} {wrong / trials:>8.1%} {predicted:>10.1%}")

if __name__ == "__main__":
    main()
