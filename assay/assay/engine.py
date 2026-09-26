"""Running a suite over a dataset and separating the good rows from the bad."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .rules import ERROR, WARN


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fieldnames=None):
    rows = list(rows)
    fieldnames = fieldnames or (list(rows[0].keys()) if rows else [])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


@dataclass
class Report:
    suite: str
    results: list
    total_rows: int
    bad_rows: set = field(default_factory=set)

    @property
    def errors(self):
        return [r for r in self.results if r.rule.severity == ERROR and not r.passed]

    @property
    def warnings(self):
        return [r for r in self.results if r.rule.severity == WARN and not r.passed]

    @property
    def ok(self) -> bool:
        """A run passes only if no ERROR rule fired. Warnings never fail a gate."""
        return not self.errors

    @property
    def clean_rows(self) -> int:
        return self.total_rows - len(self.bad_rows)

    @property
    def fired(self) -> set:
        """Ids of every rule that found something, whatever its severity."""
        return {r.rule.id for r in self.results if not r.passed}

    def as_dict(self):
        return {
            "suite": self.suite, "total_rows": self.total_rows,
            "clean_rows": self.clean_rows, "quarantined_rows": len(self.bad_rows),
            "ok": self.ok,
            "rules": [{
                "id": r.rule.id, "kind": r.rule.kind, "severity": r.rule.severity,
                "description": r.rule.describe(), "violations": len(r.violations),
                "rate": round(r.rate, 6), "passed": r.passed,
                "examples": [{"row": v.row, "value": v.value, "detail": v.detail}
                             for v in r.violations[:5]],
            } for r in self.results],
        }


def run(suite, rows, refs=None):
    ctx = {"refs": refs or {}}
    results, bad = [], set()
    for rule in suite.rules:
        res = rule.run(rows, ctx)
        results.append(res)
        if rule.severity == ERROR:
            # row=-1 means the whole table failed, not one row -- it fails the
            # run without quarantining anything, since there is no row to pull
            bad.update(v.row for v in res.violations if v.row >= 0)
    return Report(suite=suite.name, results=results, total_rows=len(rows), bad_rows=bad)


def split(rows, report):
    """Return (clean, quarantined) preserving original order."""
    clean, dirty = [], []
    for i, r in enumerate(rows):
        (dirty if i in report.bad_rows else clean).append(r)
    return clean, dirty
