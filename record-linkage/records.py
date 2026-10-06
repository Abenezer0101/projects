"""The record set: 44 real spellings of 10 stations, and a hand-written truth map.

These strings are the actual distinct values of `start_station`/`end_station`
in bikeshare-data-cleaning/data/trips_raw.csv. The rides in that file are
generated, but the corruption patterns are the ones that project documents as
real: inconsistent case, padded whitespace, and abbreviations ("Pk", "St.").

The truth map below is written by hand, by reading the 44 strings. That matters:
deriving it by normalising the strings would be scoring the matcher against
its own normaliser, which is no test at all. `validate()` asserts the map
covers exactly the strings the file contains, so a new spelling appearing in
the data fails loudly rather than being silently dropped from the denominator.
"""

from __future__ import annotations

import csv
import pathlib
from collections import Counter

DATA = (pathlib.Path(__file__).resolve().parent.parent
        / "bikeshare-data-cleaning" / "data" / "trips_raw.csv")

# Hand-labelled: every observed spelling -> the station it actually is.
TRUTH: dict[str, str] = {
    "  Atlantic Station ": "Atlantic Station",
    "ATLANTIC STATION": "Atlantic Station",
    "Atlantic Station": "Atlantic Station",
    "atlantic station": "Atlantic Station",

    "  Centennial Olympic Park ": "Centennial Olympic Park",
    "CENTENNIAL OLYMPIC PARK": "Centennial Olympic Park",
    "Centennial Olympic Park": "Centennial Olympic Park",
    "Centennial Olympic Pk": "Centennial Olympic Park",
    "centennial olympic park": "Centennial Olympic Park",

    "  Georgia State University ": "Georgia State University",
    "GEORGIA STATE UNIVERSITY": "Georgia State University",
    "Georgia State University": "Georgia State University",
    "georgia state university": "Georgia State University",

    "  Grant Park ": "Grant Park",
    "GRANT PARK": "Grant Park",
    "Grant Park": "Grant Park",
    "Grant Pk": "Grant Park",
    "grant park": "Grant Park",

    "  Krog Street Market ": "Krog Street Market",
    "KROG STREET MARKET": "Krog Street Market",
    "Krog St. Market": "Krog Street Market",
    "Krog Street Market": "Krog Street Market",
    "krog street market": "Krog Street Market",

    "  Little Five Points ": "Little Five Points",
    "LITTLE FIVE POINTS": "Little Five Points",
    "Little Five Points": "Little Five Points",
    "little five points": "Little Five Points",

    "  Midtown MARTA ": "Midtown MARTA",
    "MIDTOWN MARTA": "Midtown MARTA",
    "Midtown MARTA": "Midtown MARTA",
    "midtown marta": "Midtown MARTA",

    "  Piedmont Park ": "Piedmont Park",
    "PIEDMONT PARK": "Piedmont Park",
    "Piedmont Park": "Piedmont Park",
    "Piedmont Pk": "Piedmont Park",
    "piedmont park": "Piedmont Park",

    "  Ponce City Market ": "Ponce City Market",
    "PONCE CITY MARKET": "Ponce City Market",
    "Ponce City Market": "Ponce City Market",
    "ponce city market": "Ponce City Market",

    "  West End ": "West End",
    "WEST END": "West End",
    "West End": "West End",
    "west end": "West End",
}


def observed_spellings(path: pathlib.Path = DATA) -> Counter:
    counts: Counter = Counter()
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            for field in ("start_station", "end_station"):
                value = row.get(field)
                if value:
                    counts[value] += 1
    return counts


def validate(path: pathlib.Path = DATA) -> None:
    observed = set(observed_spellings(path))
    labelled = set(TRUTH)
    missing = observed - labelled
    extra = labelled - observed
    if missing:
        raise AssertionError(f"unlabelled spellings in the data: {sorted(missing)}")
    if extra:
        raise AssertionError(f"labelled spellings absent from the data: {sorted(extra)}")


def records() -> list[str]:
    return sorted(TRUTH)


def true_pairs(items: list[str]) -> set[tuple[int, int]]:
    """Index pairs that refer to the same station."""
    return {(i, j)
            for i in range(len(items)) for j in range(i + 1, len(items))
            if TRUTH[items[i]] == TRUTH[items[j]]}
