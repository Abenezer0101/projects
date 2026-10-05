"""Hourly bike trips, from the Day 13 project's committed data.

Unlike the daily totals (which Day 29 showed are i.i.d. with no weekly
structure), the HOURLY series has real periodicity: the generator draws each
trip's hour from a commute-shaped distribution on weekdays and a
leisure-shaped one at weekends. Mean trips by hour peak at 9.57 at 08:00 and
bottom out at 0.53 at 03:00, an 18.8x swing.

That cycle is the point. Any detector that treats the raw series as
exchangeable will call every rush hour an anomaly.

The rides are generated -- that project's README says so -- but the daily
cycle is structure the file actually contains, which is what this needs.
"""

from __future__ import annotations

import csv
import datetime
import pathlib
from collections import Counter

DATA = (pathlib.Path(__file__).resolve().parent.parent
        / "bikeshare-data-cleaning" / "data" / "trips_clean.csv")
PERIOD = 24


def hourly_counts(path: pathlib.Path = DATA) -> tuple[list[datetime.datetime], list[float]]:
    """Trips per clock hour, as a contiguous series with explicit zeros.

    Hours with no trips are absent from the file. Reading only the keys
    present would silently close those gaps and shift every later point
    relative to the 24-hour cycle, so the gaps are filled with zeros and the
    timestamps are returned alongside.
    """
    with open(path, newline="") as fh:
        counts = Counter(row["started_at"][:13] for row in csv.DictReader(fh))
    keys = sorted(counts)
    start = datetime.datetime.strptime(keys[0], "%Y-%m-%d %H")
    end = datetime.datetime.strptime(keys[-1], "%Y-%m-%d %H")
    n = int((end - start).total_seconds() // 3600) + 1
    stamps = [start + datetime.timedelta(hours=i) for i in range(n)]
    values = [float(counts.get(s.strftime("%Y-%m-%d %H"), 0)) for s in stamps]
    return stamps, values


def check_hourly(stamps: list[datetime.datetime]) -> None:
    for earlier, later in zip(stamps, stamps[1:]):
        if (later - earlier) != datetime.timedelta(hours=1):
            raise ValueError(f"gap between {earlier} and {later}")
