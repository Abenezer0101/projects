"""Auditing the rules themselves, by breaking the data on purpose.

A rule suite tells you whether the data is bad. Nothing tells you whether the
suite is any good -- and a suite that passes on garbage is worse than no suite,
because it manufactures confidence. The failure is silent by construction: the
gate is green, so nobody looks.

So: corrupt a known-good dataset in known ways and check whether the suite
notices. Each corruption is one a real pipeline actually suffers -- a units
change upstream, two columns swapped in a join, a partial load that drops rows,
an ETL that starts emitting blanks. What comes back is a list of the
corruptions your rules are blind to, which is the useful half.

Mutations never touch the caller's rows; each returns a fresh copy.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .engine import run
from .rules import ERROR, as_number, is_null


@dataclass
class Mutation:
    name: str
    detail: str
    apply: object          # rows -> rows

    def __call__(self, rows):
        return self.apply(rows)


def _copy(rows):
    return [dict(r) for r in rows]


def _targets(rows, column, frac, rnd, need_value=True):
    idx = [i for i, r in enumerate(rows)
           if not need_value or not is_null(r.get(column))]
    k = max(1, int(len(idx) * frac)) if idx else 0
    return set(rnd.sample(idx, min(k, len(idx))))


# ------------------------------------------------------------- corruptions

def blank_out(column, frac=0.05, seed=1):
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        for i in _targets(out, column, frac, rnd):
            out[i][column] = ""
        return out
    return Mutation("blank_out", f"{frac:.0%} of {column} emptied", apply)


def duplicate_rows(frac=0.03, seed=2):
    """A re-run of a loader that appends instead of replacing."""
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        k = max(1, int(len(out) * frac))
        out.extend(dict(r) for r in rnd.sample(out, min(k, len(out))))
        return out
    return Mutation("duplicate_rows", f"{frac:.0%} of rows appended again", apply)


def drop_rows(frac=0.2, seed=3):
    """A partial load. Nothing in the surviving rows looks wrong."""
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        keep = sorted(rnd.sample(range(len(out)), int(len(out) * (1 - frac))))
        return [out[i] for i in keep]
    return Mutation("drop_rows", f"{frac:.0%} of rows silently missing", apply)


def shift_decimal(column, factor=10, frac=0.04, seed=4):
    """A decimal point in the wrong place on some rows."""
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        for i in _targets(out, column, frac, rnd):
            n = as_number(out[i][column])
            if n is not None:
                out[i][column] = f"{n * factor:g}"
        return out
    return Mutation("shift_decimal", f"{frac:.0%} of {column} multiplied by {factor}", apply)


def rescale(column, factor=1.609):
    """A units change upstream -- every row, consistently, no nulls, no gaps."""
    def apply(rows):
        out = _copy(rows)
        for r in out:
            n = as_number(r.get(column))
            if n is not None:
                r[column] = f"{n * factor:g}"
        return out
    return Mutation("rescale", f"all of {column} multiplied by {factor:g} (units change)", apply)


def swap_columns(a, b):
    """Two columns crossed in a join or a bad header row."""
    def apply(rows):
        out = _copy(rows)
        for r in out:
            r[a], r[b] = r.get(b), r.get(a)
        return out
    return Mutation("swap_columns", f"{a} and {b} swapped", apply)


def unknown_category(column, value="UNSPECIFIED", frac=0.05, seed=5):
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        for i in _targets(out, column, frac, rnd):
            out[i][column] = value
        return out
    return Mutation("unknown_category", f"{frac:.0%} of {column} set to '{value}'", apply)


def pad_whitespace(column, frac=0.1, seed=6):
    """Invisible on screen, and it breaks every join and GROUP BY."""
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        for i in _targets(out, column, frac, rnd):
            out[i][column] = f"  {out[i][column]} "
        return out
    return Mutation("pad_whitespace", f"{frac:.0%} of {column} padded with spaces", apply)


def reverse_pair(a, b, frac=0.03, seed=7):
    """Start and end crossed on some rows -- negative durations."""
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        for i in _targets(out, a, frac, rnd):
            out[i][a], out[i][b] = out[i].get(b), out[i].get(a)
        return out
    return Mutation("reverse_pair", f"{frac:.0%} of rows have {a}/{b} crossed", apply)


def inject_outlier(column, factor=1000, seed=8):
    """One absurd value. Enough to move a mean, small enough to hide in a table."""
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        idx = [i for i, r in enumerate(out) if as_number(r.get(column)) is not None]
        if idx:
            i = rnd.choice(idx)
            out[i][column] = f"{as_number(out[i][column]) * factor:g}"
        return out
    return Mutation("inject_outlier", f"one value in {column} multiplied by {factor}", apply)


def truncate_values(column, chars=1, frac=0.04, seed=9):
    """Ids chopped by a fixed-width export -- joins start missing."""
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        for i in _targets(out, column, frac, rnd):
            v = str(out[i][column])
            out[i][column] = v[:-chars] if len(v) > chars else v
        return out
    return Mutation("truncate_values", f"{frac:.0%} of {column} truncated", apply)


def corrupt_type(column, value="n/a-see-notes", frac=0.03, seed=10):
    def apply(rows):
        rnd, out = random.Random(seed), _copy(rows)
        for i in _targets(out, column, frac, rnd):
            out[i][column] = value
        return out
    return Mutation("corrupt_type", f"{frac:.0%} of {column} replaced with text", apply)


# ---------------------------------------------------------------- scoring

@dataclass
class Finding:
    mutation: Mutation
    caught: bool
    by: list           # ids of the ERROR rules that noticed

    @property
    def name(self):
        return self.mutation.name


@dataclass
class Audit:
    findings: list
    baseline_ok: bool
    rules: int

    @property
    def caught(self):
        return [f for f in self.findings if f.caught]

    @property
    def missed(self):
        return [f for f in self.findings if not f.caught]

    @property
    def score(self):
        return len(self.caught) / len(self.findings) if self.findings else None

    def as_dict(self):
        return {"rules": self.rules, "mutations": len(self.findings),
                "caught": len(self.caught), "score": self.score,
                "baseline_ok": self.baseline_ok,
                "findings": [{"mutation": f.mutation.name, "detail": f.mutation.detail,
                              "caught": f.caught, "by": f.by} for f in self.findings]}


def audit(suite, rows, mutations, refs=None):
    """Run every mutation and record which ERROR rules noticed.

    A rule 'notices' if it newly fails, or fails MORE than it did on the clean
    data. Both are needed: real data is already imperfect, so a suite usually
    has rules failing at baseline, and only counting newly-failing rules would
    miss a corruption that deepens an existing problem. Counting only increases
    would in turn miss `drop_rows`, where violations go DOWN and the sole
    signal is a row-count rule that was passing and now is not.
    """
    base = run(suite, rows, refs)
    base_counts = {r.rule.id: len(r.violations) for r in base.results}
    error_ids = {r.id for r in suite.rules if r.severity == ERROR}

    findings = []
    for m in mutations:
        rep = run(suite, m(rows), refs)
        noticed = []
        for r in rep.results:
            if r.rule.id not in error_ids:
                continue
            before = base_counts.get(r.rule.id, 0)
            if len(r.violations) > before or (before == 0 and not r.passed):
                noticed.append(r.rule.id)
        findings.append(Finding(m, bool(noticed), sorted(noticed)))

    return Audit(findings=findings, baseline_ok=base.ok, rules=len(suite.rules))
