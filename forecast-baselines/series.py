"""The series under test: daily bike trips, from the Day 13 project's data.

PROVENANCE, stated up front because it decides what this project can claim.
The roadmap asked for a real series. The only external source available
(Open-Meteo's historical archive) is blocked by this environment's network
policy, and the two real-ish series already in the repository are 15 and 21
points long -- too short for a walk-forward evaluation with a weekly lag. So
this uses `bikeshare-data-cleaning/data/trips_clean.csv`, whose own README
says plainly: "the defects are real patterns, the rides are generated."

That is a limitation, and it is also the one thing that makes the headline
result provable rather than merely observed. With real data you can rank
forecasters but never know how close the winner is to the best any forecaster
could do. Here the generating process is a readable line of Python, so the
irreducible error has a closed form -- see floor.py.
"""

from __future__ import annotations

import csv
import pathlib
from collections import Counter

DATA = (pathlib.Path(__file__).resolve().parent.parent
        / "bikeshare-data-cleaning" / "data" / "trips_clean.csv")


def daily_counts(path: pathlib.Path = DATA) -> tuple[list[str], list[float]]:
    """Trips per calendar day, in date order, with no gaps assumed.

    Days with zero trips would be missing from the file entirely rather than
    present as zeros, so the dates are returned alongside the values and
    `check_contiguous` verifies the assumption instead of trusting it.
    """
    with open(path, newline="") as fh:
        counts = Counter(row["started_at"][:10] for row in csv.DictReader(fh))
    dates = sorted(counts)
    return dates, [float(counts[d]) for d in dates]


def check_contiguous(dates: list[str]) -> None:
    """A lag-7 model is meaningless if the index skips days."""
    import datetime

    parsed = [datetime.date.fromisoformat(d) for d in dates]
    for earlier, later in zip(parsed, parsed[1:]):
        if (later - earlier).days != 1:
            raise ValueError(f"gap in the series between {earlier} and {later}")
